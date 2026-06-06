import sys
import argparse
import time
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass

def create_mock_data():
    db = get_db()
    try:
        # Limpiar datos demo anteriores no deseados (como Empresa Demo S.A.)
        old_empresas = db.query(models.Empresa).filter(models.Empresa.nombre != "VenridesCafé").all()
        if old_empresas:
            for old_emp in old_empresas:
                print(f"[-] Eliminando datos demo antiguos de: {old_emp.nombre}")
                db.delete(old_emp)
            db.commit()

        empresa = db.query(models.Empresa).filter(models.Empresa.nombre == "VenridesCafé").first()
        if not empresa:
            empresa = models.Empresa(nombre="VenridesCafé", activo=True)
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            print(f"[+] Empresa creada: {empresa.nombre} (ID: {empresa.id})")
        else:
            print(f"[*] La empresa {empresa.nombre} ya existe (ID: {empresa.id})")

        configs = [
            ("HERMES_API_URL", "http://hermes:8080/v1", "API"),
            ("ODOO_URL", "https://cafe.venrides.com", "API"),
            ("ODOO_DB", "vencafedb", "API"),
            ("ODOO_API_KEY", "531b6891e88ad09cbb2343eb73c2f2f398ff5ef0", "API"),
            ("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/agent-trigger", "API"),
            ("CONSOLIDACION_SEMANAL", "0 18 * * 5", "CRON")
        ]
        for clave, valor, tipo in configs:
            ex_conf = db.query(models.ConfiguracionGlobal).filter(
                models.ConfiguracionGlobal.empresa_id == empresa.id,
                models.ConfiguracionGlobal.clave == clave
            ).first()
            if not ex_conf:
                new_conf = models.ConfiguracionGlobal(empresa_id=empresa.id, clave=clave, valor=valor, tipo=tipo)
                db.add(new_conf)
                print(f"[+] Configuración creada: {clave} = {valor}")
        db.commit()

        agentes_def = [
            ("Agente Administrativo", "Responsable de la integración de Odoo, conciliaciones, facturación y reportes financieros.", 0, ""),
            ("Agente de Marketing", "Manejo de campañas, Telegram bot, Live-Chat y contenido de redes sociales para VenridesCafé.", 0, ""),
            ("Agente de Operaciones", "Gestión de checklists de negocio, auditoría de procesos, watchdog de cuota y tareas de soporte.", 1, "Verificar token Google")
        ]
        
        agentes_map = {}
        for nombre, rol, status, tarea_act in agentes_def:
            ex_agente = db.query(models.Agente).filter(
                models.Agente.empresa_id == empresa.id,
                models.Agente.nombre == nombre
            ).first()
            if not ex_agente:
                ex_agente = models.Agente(empresa_id=empresa.id, nombre=nombre, rol_prompt=rol, status=status, tarea_actual=tarea_act)
                db.add(ex_agente)
                db.commit()
                db.refresh(ex_agente)
                print(f"[+] Agente creado: {nombre}")
            else:
                ex_agente.status = status
                ex_agente.tarea_actual = tarea_act
                db.commit()
            agentes_map[nombre] = ex_agente.id
        
        # Tareas iniciales de Hermes
        tareas_def = [
            ("Verificar estado de Odoo", "Validar conexión XML-RPC al servidor de Odoo en cafe.venrides.com.", "Hecho", "Agente Administrativo"),
            ("Verificar token Google", "Validar acceso a token Google en /opt/data/google_test.py.", "Progreso", "Agente de Operaciones"),
            ("Obtener metadatos Gmail", "Recuperar últimos 5 correos con detalles de Gmail (requiere aprobación por scopes).", "Aprobacion", "Agente de Operaciones"),
            ("Planificación Calendario Semanal", "Generar copys y calendario de contenido para redes sociales.", "Pendiente", "Agente de Marketing"),
            ("Generar informe de recuperación", "Crea reporte cuando se recupera la cuota del API.", "Pendiente", "Agente de Operaciones")
        ]

        for titulo, desc, estado, agente_name in tareas_def:
            agente_id = agentes_map.get(agente_name)
            ex_tarea = db.query(models.TareaKanban).filter(
                models.TareaKanban.empresa_id == empresa.id,
                models.TareaKanban.titulo == titulo
            ).first()
            if not ex_tarea:
                new_tarea = models.TareaKanban(
                    empresa_id=empresa.id,
                    agente_id=agente_id,
                    titulo=titulo,
                    descripcion=desc,
                    estado=estado
                )
                db.add(new_tarea)
                print(f"[+] Tarea creada: {titulo} ({estado})")
        db.commit()

        # Logs iniciales
        logs_def = [
            (None, "[SISTEMA] Canal de comunicación establecido con el gateway principal Hermes."),
            ("Agente Administrativo", "[ÉXITO] Conexión establecida con Odoo v18 (DB: vencafedb). Estado del servidor: OK."),
            ("Agente de Operaciones", "Iniciando verificación del token de Google en el sandbox (/opt/data/google_test.py)."),
            ("Agente de Operaciones", "[ATENCIÓN] Error de permisos: el token carece del scope 'gmail.readonly'. Requiere aprobación para regenerar token.")
        ]
        
        for agente_name, mensaje in logs_def:
            agente_id = agentes_map.get(agente_name) if agente_name else None
            ex_log = db.query(models.LogAuditoria).filter(
                models.LogAuditoria.empresa_id == empresa.id,
                models.LogAuditoria.mensaje == mensaje
            ).first()
            if not ex_log:
                new_log = models.LogAuditoria(
                    empresa_id=empresa.id,
                    agente_id=agente_id,
                    mensaje=mensaje
                )
                db.add(new_log)
        db.commit()

        # Siembra de Grupos
        grupos_def = [
            ("Administradores", '["all"]'),
            ("Operadores", '["read", "write"]')
        ]
        grupos_map = {}
        for nombre, perms in grupos_def:
            ex_grupo = db.query(models.Grupo).filter(models.Grupo.nombre == nombre).first()
            if not ex_grupo:
                ex_grupo = models.Grupo(nombre=nombre, permisos=perms)
                db.add(ex_grupo)
                db.commit()
                db.refresh(ex_grupo)
                print(f"[+] Grupo creado: {nombre}")
            grupos_map[nombre] = ex_grupo.id

        # Siembra de Usuarios
        import hashlib
        admin_pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        op_pwd_hash = hashlib.sha256("op123".encode()).hexdigest()
        usuarios_def = [
            ("admin", admin_pwd_hash, "Administrador ERPIA", True, "Administradores"),
            ("operador", op_pwd_hash, "Operador de Turno", True, "Operadores")
        ]
        for username, pwd_hash, full_name, activo, grupo_name in usuarios_def:
            ex_user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
            grupo_id = grupos_map.get(grupo_name)
            if not ex_user:
                ex_user = models.Usuario(
                    username=username,
                    hashed_password=pwd_hash,
                    full_name=full_name,
                    activo=activo,
                    grupo_id=grupo_id
                )
                db.add(ex_user)
                print(f"[+] Usuario creado: {username}")
        db.commit()

        # Siembra de Notas (Obsidian Wiki)
        notas_def = [
            ("Instrucciones Generales", """# Instrucciones Generales para VenridesCafé

Bienvenido al panel central de control de agentes de **VenridesCafé**. 
Este sistema gestiona e interconecta nuestros flujos de negocio automáticos.

### Agentes Disponibles
- [[Agente Administrativo]]: Se encarga de conciliar pagos y facturar en Odoo.
- [[Agente de Marketing]]: Redacta copys y envía alertas por redes sociales.
- [[Agente de Operaciones]]: Audita tareas y controla la cuota del API.

Para dudas adicionales, revisa la [[Guía de Soporte de Hermes]]."""),
            ("Agente Administrativo", """# Agente Administrativo

Este agente es responsable de la integración directa con Odoo v18.

### Credenciales y Variables
Las configuraciones están mapeadas en el panel izquierdo del sistema:
- **Base de Datos Odoo:** vencafedb
- **URL Servidor:** https://cafe.venrides.com

### Tareas Principales
- Conciliar facturas pendientes contra transacciones bancarias.
- Emitir reportes semanales al administrador.

Ver también: [[Instrucciones Generales]]."""),
            ("Agente de Marketing", """# Agente de Marketing

Se encarga de la gestión de redes sociales, Telegram bot y Live-Chat.

### Tareas
- Generar copys con promociones semanales.
- Monitorear respuestas automáticas de clientes.

Ver también: [[Instrucciones Generales]]."""),
            ("Agente de Operaciones", """# Agente de Operaciones

Watchdog principal y auditor de cuota del API.

### Tareas
- Verificación del token de Google en el script `/opt/data/google_test.py`.
- Generar informe de recuperación cuando hay caídas de servicio.

Ver también: [[Instrucciones Generales]]."""),
            ("Guía de Soporte de Hermes", """# Guía de Soporte de Hermes

En caso de fallos en la conexión:
1. Revisa que el servicio `hermes` de Docker esté levantado en el VPS.
2. Valida la URL de la API: http://hermes:8080/v1.

Ver también: [[Instrucciones Generales]].""")
        ]

        for titulo, contenido in notas_def:
            ex_nota = db.query(models.Nota).filter(
                models.Nota.empresa_id == empresa.id,
                models.Nota.titulo == titulo
            ).first()
            if not ex_nota:
                new_nota = models.Nota(
                    empresa_id=empresa.id,
                    titulo=titulo,
                    contenido=contenido
                )
                db.add(new_nota)
                print(f"[+] Nota wiki creada: {titulo}")
        db.commit()

        print("[✓] Carga de datos demo completada con éxito.")
    except Exception as e:
        print(f"[!] Error al cargar datos: {e}")
    finally:
        db.close()


def simulate_agent_run(agente_id: int, task_title: str, critical: bool):
    db = get_db()
    try:
        agente = db.query(models.Agente).filter(models.Agente.id == agente_id).first()
        if not agente:
            print(f"[!] Agente con ID {agente_id} no encontrado.")
            return

        print(f"[*] Iniciando simulación para el agente: {agente.nombre}...")
        
        agente.status = 1
        agente.tarea_actual = task_title
        db.commit()
        
        tarea = models.TareaKanban(
            empresa_id=agente.empresa_id,
            agente_id=agente.id,
            titulo=task_title,
            descripcion=f"Simulación de ejecución de la tarea: {task_title}",
            estado="Progreso"
        )
        db.add(tarea)
        db.commit()
        db.refresh(tarea)

        log1 = models.LogAuditoria(
            empresa_id=agente.empresa_id,
            agente_id=agente.id,
            mensaje=f"Iniciando ejecución de la tarea: {task_title}"
        )
        db.add(log1)
        db.commit()

        time.sleep(2)

        log2 = models.LogAuditoria(
            empresa_id=agente.empresa_id,
            agente_id=agente.id,
            mensaje=f"Procesando datos internos. Consultando configuraciones globales de la empresa."
        )
        db.add(log2)
        db.commit()

        time.sleep(2)

        if critical:
            log3 = models.LogAuditoria(
                empresa_id=agente.empresa_id,
                agente_id=agente.id,
                mensaje=f"[ATENCIÓN] La tarea '{task_title}' requiere aprobación humana para continuar. Ejecución pausada."
            )
            db.add(log3)
            
            tarea.estado = "Aprobacion"
            agente.status = 2
            db.commit()
            print(f"[!] Agente {agente.nombre} bloqueado en espera de aprobación humana.")
        else:
            log3 = models.LogAuditoria(
                empresa_id=agente.empresa_id,
                agente_id=agente.id,
                mensaje=f"[ÉXITO] Tarea '{task_title}' completada correctamente."
            )
            db.add(log3)
            
            tarea.estado = "Hecho"
            agente.status = 0
            agente.tarea_actual = ""
            db.commit()
            print(f"[✓] Agente {agente.nombre} finalizó su tarea de manera autónoma.")

    except Exception as e:
        print(f"[!] Error en simulación: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI Runner de ERPIA")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("create-mock-data", help="Crea datos demo iniciales en la base de datos.")

    sim_parser = subparsers.add_parser("simulate", help="Simula la ejecución de una tarea por un agente.")
    sim_parser.add_argument("agente_id", type=int, help="ID del agente a simular")
    sim_parser.add_argument("--task", type=str, required=True, help="Título de la tarea")
    sim_parser.add_argument("--critical", action="store_true", help="Detener en aprobación humana")

    args = parser.parse_args()

    if args.command == "create-mock-data":
        create_mock_data()
    elif args.command == "simulate":
        simulate_agent_run(args.agente_id, args.task, args.critical)
    else:
        parser.print_help()
