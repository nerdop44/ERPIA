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
        empresa = db.query(models.Empresa).filter(models.Empresa.nombre == "Empresa Demo S.A.").first()
        if not empresa:
            empresa = models.Empresa(nombre="Empresa Demo S.A.", activo=True)
            db.add(empresa)
            db.commit()
            db.refresh(empresa)
            print(f"[+] Empresa creada: {empresa.nombre} (ID: {empresa.id})")
        else:
            print(f"[*] La empresa {empresa.nombre} ya existe (ID: {empresa.id})")

        configs = [
            ("HERMES_API_URL", "http://hermes:8080/v1", "API"),
            ("ODOO_URL", "https://odoo.venrides.com", "API"),
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

        agentes = [
            ("Agente Administrativo", "Gestionar conciliaciones bancarias y pagos en Odoo.", 0),
            ("Agente de Marketing", "Redacción de copys semanales y publicación de anuncios.", 0),
            ("Agente de Soporte", "Monitoreo del buzón de soporte técnico y respuestas automatizadas.", 0)
        ]
        for nombre, rol, status in agentes:
            ex_agente = db.query(models.Agente).filter(
                models.Agente.empresa_id == empresa.id,
                models.Agente.nombre == nombre
            ).first()
            if not ex_agente:
                new_agente = models.Agente(empresa_id=empresa.id, nombre=nombre, rol_prompt=rol, status=status)
                db.add(new_agente)
                print(f"[+] Agente creado: {nombre}")
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
