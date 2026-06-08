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

3. **[2026-06-06] Implementación Completa de la Fase 2 (Auth, Ajustes y Obsidian Wiki):**
   - Incorporación de los modelos avanzados de Base de Datos para Usuarios, Grupos y Notas de la Wiki en PostgreSQL.
   - Implementación de los endpoints REST en FastAPI para login con token, CRUD de usuarios/grupos y guardado de notas.
   - Integración en el frontend de la pantalla de login persistente, menú de App Switcher, modo oscuro global, barras laterales redimensionables y el visualizador de grafo interactivo en Canvas (fuerza dirigida).
   - Despliegue de los cambios en el repositorio de GitHub y sincronización en producción en el VPS mediante reconstrucción de contenedores y siembra de base de datos en caliente.
   - Verificación funcional exitosa en el puerto 8000 del VPS con registro de capturas en el walkthrough.

4. **[2026-06-06] Implementación de la Fase 3 (Pestañas Multitarea, Chat de Agente y Gestión de Credenciales):**
   - Integrado el modal y la lógica CRUD (listar, crear, eliminar) para la gestión de credenciales API (Gemini/OpenRouter/Local VPS) por empresa asociada en Ajustes.
   - Implementado el buscador de NotebookLM y la exportación de la Wiki en formato Markdown unificado.
   - Diseñada e implementada la lógica de instanciación dinámica de pestañas de trabajo independientes por cada agente en la barra superior del espacio de trabajo.
   - Creado el panel de chat interactivo y el editor de parámetros/configuración del LLM para cada agente, sincronizado en tiempo real por WebSockets.

5. **[2026-06-08] Implementación de la Fase 4 (Perfil de Empresa, Actividades, Crons, Skills/MCPs y Catalogo de Tools):**
   - Modelos y endpoints para perfil rico de empresa (RIF, misión, visión, canales de comunicación, vertical de negocio).
   - Endpoints CRUD para actividades de agente (tipo, título, estado) y crons programados (expresión cron, activo/inactivo).
   - Catálogo estático de tools/herramientas por proveedor (Google, OpenRouter, Hermes, MCP) con endpoint de consulta.
   - Gestión de skills, MCPs y APIs por agente en el workspace (habilidades nativas editables inline, badges de skills/MCPs activos).
   - Panel de perfil de empresa en Ajustes con formulario completo y guardado vía API.
   - Sidebar de resumen de empresa con canales de comunicación y métricas en tiempo real.
   - Historial de actividades y programación de crons en el workspace del agente.
   - Detalle de credenciales con visibilidad admin, edición y opción de revertir a snapshot.
   - Corrección de errores de integración: funciones faltantes del frontend (switchWsTab, addNativeSkill, addSkillToAgent, saveAgentSkills, CRUD de actividades y crons), referencia a elemento inexistente agent-profile-skills, login sin is_admin, y panel empresa-perfil sin implementar.
