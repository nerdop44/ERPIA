# Contexto Técnico del Proyecto ERPIA

## Ecosistema y Arquitectura
ERPIA es un plano de control unificado multi-empresa para la orquestación de agentes de IA.

```mermaid
graph TD
    User[Usuario / Admin] -->|UI Dashboard| Frontend(Columna Izquierda: Configs | Centro: Kanban | Derecha: Logs)
    Frontend -->|WebSockets / REST| Backend[FastAPI Backend]
    Backend -->|SQLAlchemy| DB[(PostgreSQL DB)]
    Backend -->|Webhook / API| n8n[n8n Workflow Engine]
    Backend -->|API / CLI| Agent[Agentes / Antigravity Runner]
    n8n -->|Interactúa| Hermes[Hermes AI Gateway]
    Agent -->|Ejecuta / Loguea| Backend
```

## Especificaciones de Infraestructura y Despliegue
- **VPS IP:** `37.60.236.245`
- **Dominio:** `erpia.venrides.com`
- **Base de Datos:** PostgreSQL en contenedor Docker.
- **n8n:** Ejecutándose en contenedor Docker en la misma red.
- **Hermes:** Ya instalado y configurado en el VPS directamente.
- **Nginx:** Configurado como proxy inverso en el VPS para enrutar tráfico HTTP/HTTPS y WebSockets hacia el contenedor del ERP y n8n.
