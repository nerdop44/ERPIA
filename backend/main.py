import json
import hashlib
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.database import engine, Base, get_db
from backend import models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ERPIA - Agent-ERP API",
    description="Backend para la orquestación y monitoreo en tiempo real de agentes de IA Multi-Empresa.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        def json_serial(obj):
            if isinstance(obj, (datetime)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        payload = json.dumps(message, default=json_serial)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/empresas", response_model=schemas.EmpresaResponse, status_code=status.HTTP_201_CREATED)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = db.query(models.Empresa).filter(models.Empresa.nombre == empresa.nombre).first()
    if db_empresa:
        raise HTTPException(status_code=400, detail="El nombre de la empresa ya está registrado.")
    new_empresa = models.Empresa(**empresa.dict())
    db.add(new_empresa)
    db.commit()
    db.refresh(new_empresa)
    return new_empresa

@app.get("/api/empresas", response_model=List[schemas.EmpresaResponse])
def get_empresas(db: Session = Depends(get_db)):
    return db.query(models.Empresa).all()

@app.get("/api/empresas/{id}", response_model=schemas.EmpresaResponse)
def get_empresa(id: int, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return empresa

@app.post("/api/configuraciones", response_model=schemas.ConfiguracionGlobalResponse, status_code=status.HTTP_201_CREATED)
def create_configuracion(config: schemas.ConfiguracionGlobalCreate, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == config.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    new_config = models.ConfiguracionGlobal(**config.dict())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config

@app.get("/api/empresas/{empresa_id}/configuraciones", response_model=List[schemas.ConfiguracionGlobalResponse])
def get_configuraciones(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.ConfiguracionGlobal).filter(models.ConfiguracionGlobal.empresa_id == empresa_id).all()

@app.delete("/api/configuraciones/{id}")
def delete_configuracion(id: int, db: Session = Depends(get_db)):
    config = db.query(models.ConfiguracionGlobal).filter(models.ConfiguracionGlobal.id == id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
    db.delete(config)
    db.commit()
    return {"message": "Configuración eliminada correctamente."}

@app.post("/api/agentes", response_model=schemas.AgenteResponse, status_code=status.HTTP_201_CREATED)
async def create_agente(agente: schemas.AgenteCreate, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == agente.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    new_agente = models.Agente(**agente.dict())
    db.add(new_agente)
    db.commit()
    db.refresh(new_agente)
    await manager.broadcast({
        "type": "agente_creado",
        "data": {
            "id": new_agente.id,
            "empresa_id": new_agente.empresa_id,
            "nombre": new_agente.nombre,
            "rol_prompt": new_agente.rol_prompt,
            "status": new_agente.status,
            "tarea_actual": new_agente.tarea_actual
        }
    })
    return new_agente

@app.get("/api/empresas/{empresa_id}/agentes", response_model=List[schemas.AgenteResponse])
def get_agentes(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.Agente).filter(models.Agente.empresa_id == empresa_id).all()

@app.put("/api/agentes/{id}/status", response_model=schemas.AgenteResponse)
async def update_agente_status(id: int, payload: schemas.AgenteStatusUpdate, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    agente.status = payload.status
    if payload.tarea_actual is not None:
        agente.tarea_actual = payload.tarea_actual
    db.commit()
    db.refresh(agente)
    await manager.broadcast({
        "type": "agente_status_update",
        "data": {
            "id": agente.id,
            "empresa_id": agente.empresa_id,
            "nombre": agente.nombre,
            "status": agente.status,
            "tarea_actual": agente.tarea_actual
        }
    })
    return agente

@app.post("/api/tareas", response_model=schemas.TareaKanbanResponse, status_code=status.HTTP_201_CREATED)
async def create_tarea(tarea: schemas.TareaKanbanCreate, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == tarea.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if tarea.agente_id:
        agente = db.query(models.Agente).filter(models.Agente.id == tarea.agente_id).first()
        if not agente:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
    new_tarea = models.TareaKanban(**tarea.dict())
    db.add(new_tarea)
    db.commit()
    db.refresh(new_tarea)
    await manager.broadcast({
        "type": "tarea_creada",
        "data": {
            "id": new_tarea.id,
            "empresa_id": new_tarea.empresa_id,
            "agente_id": new_tarea.agente_id,
            "titulo": new_tarea.titulo,
            "descripcion": new_tarea.descripcion,
            "estado": new_tarea.estado,
            "resultado_draft": new_tarea.resultado_draft
        }
    })
    return new_tarea

@app.get("/api/empresas/{empresa_id}/tareas", response_model=List[schemas.TareaKanbanResponse])
def get_tareas(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.TareaKanban).filter(models.TareaKanban.empresa_id == empresa_id).all()

@app.put("/api/tareas/{id}", response_model=schemas.TareaKanbanResponse)
async def update_tarea(id: int, payload: schemas.TareaKanbanUpdate, db: Session = Depends(get_db)):
    tarea = db.query(models.TareaKanban).filter(models.TareaKanban.id == id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    tarea.estado = payload.estado
    if payload.resultado_draft is not None:
        tarea.resultado_draft = payload.resultado_draft
    db.commit()
    db.refresh(tarea)
    if tarea.estado == "Aprobacion" and tarea.agente_id:
        agente = db.query(models.Agente).filter(models.Agente.id == tarea.agente_id).first()
        if agente:
            agente.status = 2
            db.commit()
            await manager.broadcast({
                "type": "agente_status_update",
                "data": {
                    "id": agente.id,
                    "empresa_id": agente.empresa_id,
                    "nombre": agente.nombre,
                    "status": agente.status,
                    "tarea_actual": agente.tarea_actual
                }
            })
    await manager.broadcast({
        "type": "tarea_status_update",
        "data": {
            "id": tarea.id,
            "empresa_id": tarea.empresa_id,
            "agente_id": tarea.agente_id,
            "titulo": tarea.titulo,
            "estado": tarea.estado,
            "resultado_draft": tarea.resultado_draft
        }
    })
    return tarea

@app.put("/api/tareas/{id}/aprobar", response_model=schemas.TareaKanbanResponse)
async def aprobar_tarea(id: int, db: Session = Depends(get_db)):
    tarea = db.query(models.TareaKanban).filter(models.TareaKanban.id == id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    tarea.estado = "Hecho"
    db.commit()
    if tarea.agente_id:
        agente = db.query(models.Agente).filter(models.Agente.id == tarea.agente_id).first()
        if agente:
            agente.status = 0
            agente.tarea_actual = ""
            db.commit()
            await manager.broadcast({
                "type": "agente_status_update",
                "data": {
                    "id": agente.id,
                    "empresa_id": agente.empresa_id,
                    "nombre": agente.nombre,
                    "status": agente.status,
                    "tarea_actual": agente.tarea_actual
                }
            })
            log_msg = f"Aprobación manual concedida. Tarea '{tarea.titulo}' completada con éxito."
            new_log = models.LogAuditoria(
                empresa_id=tarea.empresa_id,
                agente_id=agente.id,
                mensaje=log_msg
            )
            db.add(new_log)
            db.commit()
            db.refresh(new_log)
            await manager.broadcast({
                "type": "nuevo_log",
                "data": {
                    "id": new_log.id,
                    "empresa_id": new_log.empresa_id,
                    "agente_id": new_log.agente_id,
                    "mensaje": new_log.mensaje,
                    "timestamp": new_log.timestamp
                }
            })
    await manager.broadcast({
        "type": "tarea_status_update",
        "data": {
            "id": tarea.id,
            "empresa_id": tarea.empresa_id,
            "agente_id": tarea.agente_id,
            "titulo": tarea.titulo,
            "estado": tarea.estado,
            "resultado_draft": tarea.resultado_draft
        }
    })
    return tarea

@app.post("/api/logs", response_model=schemas.LogAuditoriaResponse, status_code=status.HTTP_201_CREATED)
async def create_log(log: schemas.LogAuditoriaCreate, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == log.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if log.agente_id:
        agente = db.query(models.Agente).filter(models.Agente.id == log.agente_id).first()
        if not agente:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
    new_log = models.LogAuditoria(**log.dict())
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    await manager.broadcast({
        "type": "nuevo_log",
        "data": {
            "id": new_log.id,
            "empresa_id": new_log.empresa_id,
            "agente_id": new_log.agente_id,
            "mensaje": new_log.mensaje,
            "timestamp": new_log.timestamp
        }
    })
    return new_log

@app.get("/api/empresas/{empresa_id}/logs", response_model=List[schemas.LogAuditoriaResponse])
def get_logs(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.LogAuditoria).filter(models.LogAuditoria.empresa_id == empresa_id).order_by(models.LogAuditoria.timestamp.asc()).all()


# Endpoints de Autenticación
@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    pwd_hash = hashlib.sha256(payload.password.encode()).hexdigest()
    user = db.query(models.Usuario).filter(models.Usuario.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    
    if user.hashed_password != pwd_hash and user.hashed_password != payload.password:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    
    # Si la contraseña estaba en texto plano (como la siembra inicial), la actualizamos hasheada
    if user.hashed_password == payload.password:
        user.hashed_password = pwd_hash
        db.commit()
        db.refresh(user)

    return {
        "token": f"token-{user.username}",
        "usuario": user
    }

@app.get("/api/auth/me", response_model=schemas.UsuarioResponse)
def get_me(token: str, db: Session = Depends(get_db)):
    username = token.replace("token-", "")
    user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Sesión no válida.")
    return user

# CRUD Usuarios
@app.get("/api/usuarios", response_model=List[schemas.UsuarioResponse])
def get_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()

@app.post("/api/usuarios", response_model=schemas.UsuarioResponse)
def create_usuario(user: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe.")
    pwd_hash = hashlib.sha256(user.password.encode()).hexdigest()
    
    new_user = models.Usuario(
        username=user.username,
        hashed_password=pwd_hash,
        full_name=user.full_name,
        activo=user.activo,
        grupo_id=user.grupo_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.delete("/api/usuarios/{id}")
def delete_usuario(id: int, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado correctamente."}

# CRUD Grupos
@app.get("/api/grupos", response_model=List[schemas.GrupoResponse])
def get_grupos(db: Session = Depends(get_db)):
    return db.query(models.Grupo).all()

@app.post("/api/grupos", response_model=schemas.GrupoResponse)
def create_grupo(grupo: schemas.GrupoCreate, db: Session = Depends(get_db)):
    db_grupo = db.query(models.Grupo).filter(models.Grupo.nombre == grupo.nombre).first()
    if db_grupo:
        raise HTTPException(status_code=400, detail="El nombre del grupo ya existe.")
    new_grupo = models.Grupo(**grupo.dict())
    db.add(new_grupo)
    db.commit()
    db.refresh(new_grupo)
    return new_grupo

@app.delete("/api/grupos/{id}")
def delete_grupo(id: int, db: Session = Depends(get_db)):
    grupo = db.query(models.Grupo).filter(models.Grupo.id == id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado.")
    db.delete(grupo)
    db.commit()
    return {"message": "Grupo eliminado correctamente."}

# Endpoints de Notas (Obsidian Wiki)
@app.get("/api/empresas/{empresa_id}/notas", response_model=List[schemas.NotaResponse])
def get_notas(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.Nota).filter(models.Nota.empresa_id == empresa_id).all()

@app.get("/api/empresas/{empresa_id}/notas/{titulo}", response_model=schemas.NotaResponse)
def get_nota_by_titulo(empresa_id: int, titulo: str, db: Session = Depends(get_db)):
    nota = db.query(models.Nota).filter(
        models.Nota.empresa_id == empresa_id,
        models.Nota.titulo == titulo
    ).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    return nota

@app.post("/api/notas", response_model=schemas.NotaResponse)
def create_or_update_nota(nota: schemas.NotaCreate, db: Session = Depends(get_db)):
    db_nota = db.query(models.Nota).filter(
        models.Nota.empresa_id == nota.empresa_id,
        models.Nota.titulo == nota.titulo
    ).first()
    if db_nota:
        db_nota.contenido = nota.contenido
        db_nota.fecha_actualizacion = datetime.utcnow()
        db.commit()
        db.refresh(db_nota)
        return db_nota
    else:
        new_nota = models.Nota(**nota.dict())
        db.add(new_nota)
        db.commit()
        db.refresh(new_nota)
        return new_nota

@app.delete("/api/notas/{id}")
def delete_nota(id: int, db: Session = Depends(get_db)):
    nota = db.query(models.Nota).filter(models.Nota.id == id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    db.delete(nota)
    db.commit()
    return {"message": "Nota eliminada correctamente."}


# Servir archivos estáticos del frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
