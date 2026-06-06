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
from pydantic import BaseModel

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

@app.get("/api/agentes/{id}", response_model=schemas.AgenteResponse)
def get_agente_by_id(id: int, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return agente

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

@app.put("/api/agentes/{id}", response_model=schemas.AgenteResponse)
async def update_agente(id: int, payload: schemas.AgenteBase, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    
    agente.nombre = payload.nombre
    agente.rol_prompt = payload.rol_prompt
    agente.habilidades = payload.habilidades
    agente.objetivos = payload.objetivos
    agente.recursos = payload.recursos
    agente.conocimientos = payload.conocimientos
    agente.herramientas = payload.herramientas
    agente.modelo_config = payload.modelo_config
    
    db.commit()
    db.refresh(agente)
    
    await manager.broadcast({
        "type": "agente_actualizado",
        "data": {
            "id": agente.id,
            "empresa_id": agente.empresa_id,
            "nombre": agente.nombre,
            "rol_prompt": agente.rol_prompt,
            "status": agente.status,
            "tarea_actual": agente.tarea_actual,
            "habilidades": agente.habilidades,
            "objetivos": agente.objetivos,
            "recursos": agente.recursos,
            "conocimientos": agente.conocimientos,
            "herramientas": agente.herramientas,
            "modelo_config": agente.modelo_config
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


# =====================================================================
# FASE 3 - ENDPOINTS DE CREDENCIALES
# =====================================================================

@app.get("/api/empresas/{empresa_id}/credenciales", response_model=List[schemas.CredencialApiResponse])
def get_credenciales(empresa_id: int, db: Session = Depends(get_db)):
    return db.query(models.CredencialApi).filter(models.CredencialApi.empresa_id == empresa_id).all()

@app.post("/api/credenciales", response_model=schemas.CredencialApiResponse)
def create_or_update_credencial(payload: schemas.CredencialApiCreate, db: Session = Depends(get_db)):
    db_cred = db.query(models.CredencialApi).filter(
        models.CredencialApi.empresa_id == payload.empresa_id,
        models.CredencialApi.nombre == payload.nombre
    ).first()
    if db_cred:
        db_cred.proveedor = payload.proveedor
        db_cred.credencial_valor = payload.credencial_valor
        db_cred.url_endpoint = payload.url_endpoint
        db_cred.config_json = payload.config_json
        db_cred.activo = payload.activo
        db.commit()
        db.refresh(db_cred)
        return db_cred
    else:
        new_cred = models.CredencialApi(**payload.dict())
        db.add(new_cred)
        db.commit()
        db.refresh(new_cred)
        return new_cred

@app.delete("/api/credenciales/{id}")
def delete_credencial(id: int, db: Session = Depends(get_db)):
    cred = db.query(models.CredencialApi).filter(models.CredencialApi.id == id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credencial no encontrada")
    db.delete(cred)
    db.commit()
    return {"message": "Credencial eliminada correctamente."}

@app.post("/api/agentes/{agente_id}/credenciales/{credencial_id}")
def link_credencial_agente(agente_id: int, credencial_id: int, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == agente_id).first()
    cred = db.query(models.CredencialApi).filter(models.CredencialApi.id == credencial_id).first()
    if not agente or not cred:
        raise HTTPException(status_code=404, detail="Agente o credencial no encontrada")
    if cred not in agente.credenciales:
        agente.credenciales.append(cred)
        db.commit()
    return {"message": "Credencial vinculada correctamente"}

@app.delete("/api/agentes/{agente_id}/credenciales/{credencial_id}")
def unlink_credencial_agente(agente_id: int, credencial_id: int, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == agente_id).first()
    cred = db.query(models.CredencialApi).filter(models.CredencialApi.id == credencial_id).first()
    if not agente or not cred:
        raise HTTPException(status_code=404, detail="Agente o credencial no encontrada")
    if cred in agente.credenciales:
        agente.credenciales.remove(cred)
        db.commit()
    return {"message": "Credencial desvinculada correctamente"}

# =====================================================================
# FASE 3 - ENDPOINTS DE CHAT E INTEGRACIÓN CON MODELOS REALES
# =====================================================================

@app.get("/api/agentes/{agente_id}/chat", response_model=List[schemas.MensajeChatResponse])
def get_chat_history(agente_id: int, db: Session = Depends(get_db)):
    return db.query(models.MensajeChat).filter(models.MensajeChat.agente_id == agente_id).order_by(models.MensajeChat.timestamp.asc()).all()

import urllib.request
import urllib.parse

@app.post("/api/agentes/{agente_id}/chat", response_model=schemas.MensajeChatResponse)
async def send_chat_message(agente_id: int, payload: schemas.MensajeChatCreate, db: Session = Depends(get_db)):
    agente = db.query(models.Agente).filter(models.Agente.id == agente_id).first()
    if not agente:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
        
    # Guardar mensaje del usuario
    user_msg = models.MensajeChat(
        agente_id=agente_id,
        usuario_id=payload.usuario_id,
        remitente=payload.remitente,
        contenido=payload.contenido
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    
    # Notificar WebSocket del nuevo mensaje
    await manager.broadcast({
        "type": "nuevo_mensaje_chat",
        "data": {
            "id": user_msg.id,
            "agente_id": agente_id,
            "remitente": user_msg.remitente,
            "contenido": user_msg.contenido,
            "timestamp": user_msg.timestamp
        }
    })

    # Cambiar estado del agente a "Pensando" (status = 1)
    agente.status = 1
    agente.tarea_actual = "Respondiendo en el chat..."
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

    # Buscar conocimiento relevante de la wiki de esta empresa
    wiki_context = ""
    linked_notes = []
    if agente.conocimientos:
        try:
            linked_notes = json.loads(agente.conocimientos)
        except Exception:
            linked_notes = []
            
    notes = db.query(models.Nota).filter(models.Nota.empresa_id == agente.empresa_id).all()
    wiki_context_list = []
    for note in notes:
        # Añadir si está expresamente vinculada o si se menciona en el mensaje actual
        if note.titulo in linked_notes or note.titulo.lower() in payload.contenido.lower():
            wiki_context_list.append(f"Nota: {note.titulo}\nContenido:\n{note.contenido}")
            
    if wiki_context_list:
        wiki_context = "\n\n=== CONOCIMIENTO DISPONIBLE EN OBSIDIAN WIKI ===\n" + "\n---\n".join(wiki_context_list) + "\n==============================================\n"

    # Preparar Prompt de Sistema
    system_prompt = (
        f"Eres el agente '{agente.nombre}'.\n"
        f"Tu rol/instrucciones son:\n{agente.rol_prompt or ''}\n"
        f"Habilidades: {agente.habilidades or 'Ninguna'}\n"
        f"Objetivos: {agente.objetivos or 'Ninguno'}\n"
        f"{wiki_context}\n"
        f"Por favor responde de forma profesional e interactiva, alineado con tu rol. "
        f"No inventes datos ni alucines. Si no sabes algo o careces de permisos, indícalo claramente."
    )

    # Cargar historial de chat (últimos 15 mensajes)
    historial = db.query(models.MensajeChat).filter(
        models.MensajeChat.agente_id == agente_id
    ).order_by(models.MensajeChat.timestamp.desc()).limit(15).all()
    historial = list(reversed(historial))

    # Construir lista de mensajes para la API
    messages_payload = [{"role": "system", "content": system_prompt}]
    for h in historial:
        role = "assistant" if h.remitente == "agente" else "user"
        # Evitar duplicar el último mensaje recién agregado si ya viene en el historial
        if h.id != user_msg.id:
            messages_payload.append({"role": role, "content": h.contenido})
    messages_payload.append({"role": "user", "content": payload.contenido})

    # Determinar qué modelo y proveedor usar
    provider = "google"
    model_name = "gemini-1.5-flash"
    use_free_only = True
    
    if agente.modelo_config:
        try:
            cfg = json.loads(agente.modelo_config)
            provider = cfg.get("provider", provider)
            model_name = cfg.get("model", model_name)
            use_free_only = cfg.get("use_free_only", use_free_only)
        except Exception:
            pass

    respuesta_texto = ""

    # Caso especial: Hermes (conexión real al contenedor del VPS)
    if "Hermes" in agente.nombre:
        try:
            req_url = "http://hermes:8642/v1/chat/completions"
            data_payload = {
                "model": model_name,
                "messages": messages_payload
            }
            req_data = json.dumps(data_payload).encode("utf-8")
            req = urllib.request.Request(
                req_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer hermes-webui-key"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                respuesta_texto = resp_data["choices"][0]["message"]["content"]
        except Exception as e:
            respuesta_texto = f"Error al conectar con la API de Hermes en el VPS: {str(e)}. Por favor verifica que el contenedor 'hermes' esté activo."
    else:
        # Consultar mediante credenciales de la empresa
        cred = db.query(models.CredencialApi).filter(
            models.CredencialApi.empresa_id == agente.empresa_id,
            models.CredencialApi.proveedor == provider,
            models.CredencialApi.activo == True
        ).first()

        api_key = cred.credencial_valor if cred else None

        if not api_key:
            # Fallback a credencial de OpenRouter global
            fallback_cred = db.query(models.CredencialApi).filter(
                models.CredencialApi.proveedor == "openrouter",
                models.CredencialApi.activo == True
            ).first()
            if fallback_cred:
                api_key = fallback_cred.credencial_valor
                provider = "openrouter"
                
        if not api_key:
            respuesta_texto = "Error: No se encontró una API Key configurada para este proveedor en la empresa."
        else:
            try:
                if provider == "google":
                    req_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    
                    full_text = f"INSTRUCCIONES DE SISTEMA:\n{system_prompt}\n\nHISTORIAL Y MENSAJE:\n"
                    for msg in messages_payload[1:]:
                        full_text += f"{msg['role'].upper()}: {msg['content']}\n"
                    
                    data_payload = {
                        "contents": [
                            {"parts": [{"text": full_text}]}
                        ]
                    }
                    req_data = json.dumps(data_payload).encode("utf-8")
                    req = urllib.request.Request(
                        req_url,
                        data=req_data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=30) as response:
                        resp_data = json.loads(response.read().decode("utf-8"))
                        respuesta_texto = resp_data["candidates"][0]["content"]["parts"][0]["text"]

                elif provider == "openrouter":
                    req_url = "https://openrouter.ai/api/v1/chat/completions"
                    data_payload = {
                        "model": model_name,
                        "messages": messages_payload
                    }
                    req_data = json.dumps(data_payload).encode("utf-8")
                    req = urllib.request.Request(
                        req_url,
                        data=req_data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                            "HTTP-Referer": "http://erpia.venrides.com"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=30) as response:
                        resp_data = json.loads(response.read().decode("utf-8"))
                        respuesta_texto = resp_data["choices"][0]["message"]["content"]
                else:
                    respuesta_texto = f"Proveedor de modelo '{provider}' no implementado todavía."
            except Exception as e:
                respuesta_texto = f"Error al ejecutar consulta al modelo ({provider}): {str(e)}"

    # Guardar respuesta del agente
    agent_msg = models.MensajeChat(
        agente_id=agente_id,
        usuario_id=None,
        remitente="agente",
        contenido=respuesta_texto
    )
    db.add(agent_msg)
    
    # Restaurar estado del agente
    agente.status = 0
    agente.tarea_actual = ""
    db.commit()
    db.refresh(agent_msg)

    # Notificar WebSocket
    await manager.broadcast({
        "type": "nuevo_mensaje_chat",
        "data": {
            "id": agent_msg.id,
            "agente_id": agente_id,
            "remitente": agent_msg.remitente,
            "contenido": agent_msg.contenido,
            "timestamp": agent_msg.timestamp
        }
    })
    
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

    return agent_msg


# =====================================================================
# FASE 3 - ENDPOINTS DE BUSQUEDA EXTERNA / NOTEBOOKLM
# =====================================================================

class NotebookLMSearchRequest(BaseModel):
    empresa_id: int
    query: str

@app.post("/api/knowledge/notebooklm/search")
def search_external_knowledge(payload: NotebookLMSearchRequest, db: Session = Depends(get_db)):
    cred = db.query(models.CredencialApi).filter(
        models.CredencialApi.empresa_id == payload.empresa_id,
        models.CredencialApi.proveedor == "google",
        models.CredencialApi.activo == True
    ).first()
    
    api_key = cred.credencial_valor if cred else None
    
    if not api_key:
        fallback_cred = db.query(models.CredencialApi).filter(
            models.CredencialApi.proveedor == "openrouter",
            models.CredencialApi.activo == True
        ).first()
        if fallback_cred:
            api_key = fallback_cred.credencial_valor

    if not api_key:
        raise HTTPException(status_code=400, detail="No hay credenciales configuradas para realizar la búsqueda.")

    try:
        req_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        system_instructions = (
            "Eres el servicio NotebookLM Integrado de ERPIA. Tu tarea es buscar información externa y "
            "estructurar una nota de conocimiento comprensiva, detallada, útil y profesional con formato markdown. "
            "Incluye fuentes de datos de alta calidad o conceptos teóricos sólidos."
        )
        
        prompt = f"Investiga detalladamente sobre el siguiente tema y genera una nota de conocimiento estructurada:\n\n{payload.query}"
        full_text = f"INSTRUCCIONES:\n{system_instructions}\n\nTEMA:\n{prompt}"
        
        data_payload = {
            "contents": [
                {"parts": [{"text": full_text}]}
            ]
        }
        req_data = json.dumps(data_payload).encode("utf-8")
        req = urllib.request.Request(
            req_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            respuesta_texto = resp_data["candidates"][0]["content"]["parts"][0]["text"]
            
        return {
            "titulo": f"NotebookLM: {payload.query}",
            "contenido": respuesta_texto
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la consulta NotebookLM: {str(e)}")


# =====================================================================
# FASE 3 - EXPORTAR WIKI A FORMATO ZIP/JSON PARA NOTEBOOKLM/OBSIDIAN
# =====================================================================

@app.get("/api/empresas/{empresa_id}/wiki/export")
def export_wiki_vault(empresa_id: int, db: Session = Depends(get_db)):
    notas = db.query(models.Nota).filter(models.Nota.empresa_id == empresa_id).all()
    
    vault_export = []
    for nota in notas:
        vault_export.append({
            "filename": f"{nota.titulo}.md",
            "content": f"# {nota.titulo}\n\nÚltima actualización: {nota.fecha_actualizacion.isoformat()}\n\n{nota.contenido}"
        })
        
    return {
        "empresa_id": empresa_id,
        "export_date": datetime.utcnow().isoformat(),
        "notes_count": len(notas),
        "vault": vault_export
    }


# Servir archivos estáticos del frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
