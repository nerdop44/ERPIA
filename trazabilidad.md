# Trazabilidad del Proyecto ERPIA

## Contexto Inicial
- **Nombre del Proyecto:** ERPIA (ERP de Agentes de IA Multi-Empresas).
- **Objetivo:** Crear un MVP de una plataforma web robusta, modular y multi-empresa que actúe como una mesa de control centralizada para agentes de IA con orquestación mediante n8n, Hermes y Antigravity.
- **Estado:** Inicialización de archivos de contexto y entorno.
- **Entorno:** VPS IP `37.60.236.245`, base de datos PostgreSQL, dominio `erpia.venrides.com`.
- **Repositorio:** `nerdop44/ERPIA` en GitHub (Público).

## Registro de Decisiones y Cambios
1. **[2026-06-06] Planificación Aprobada:**
   - Se acordó el uso de PostgreSQL en lugar de SQLite para mayor escalabilidad y soporte multi-hilo.
   - El repositorio será público en GitHub.
   - El dominio de despliegue asignado es `erpia.venrides.com`.
   - Se crearon los archivos de alineación de personalidad y persistencia: `soul.md`, `context.md` y `agent.md`.

2. **[2026-06-06] Refactorización y Estilo Odoo 18:**
   - Rediseño completo de la interfaz de usuario (`frontend/index.html`) inspirada en Odoo 18, usando colores corporativos (#714B67) y un panel lateral tipo Chatter para logs en tiempo real.
   - Siembra de datos iniciales reales en la base de datos de **VenridesCafé** (empresa, agentes administrativo/marketing/operaciones, tokens Odoo y tareas).
   - Añadida la dependencia `websockets` en `backend/requirements.txt` para corregir la falta de soporte de WebSocket de Uvicorn.
   - Modificación del script `runner.py` para limpiar automáticamente los datos antiguos (Empresa Demo S.A.) durante la siembra.
   - Despliegue, reconstrucción y verificación exitosa de la interfaz y WebSockets en tiempo real en el puerto :8000 del VPS.
