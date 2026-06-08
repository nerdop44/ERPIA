from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ─────────────────────────────────────────
# EMPRESA
# ─────────────────────────────────────────
class EmpresaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    activo: Optional[bool] = True

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class EmpresaPerfilUpdate(BaseModel):
    """Schema para actualizar el perfil completo de una empresa."""
    nombre: Optional[str] = None
    rif: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    pais: Optional[str] = None
    sitio_web: Optional[str] = None
    mision: Optional[str] = None
    vision: Optional[str] = None
    vertical_negocio: Optional[str] = None
    descripcion_actividad: Optional[str] = None
    objetivos_generales: Optional[str] = None
    canales_comunicacion: Optional[str] = None  # JSON string


class EmpresaPerfilResponse(BaseModel):
    id: int
    nombre: str
    activo: bool
    fecha_creacion: datetime
    rif: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    pais: Optional[str] = None
    sitio_web: Optional[str] = None
    mision: Optional[str] = None
    vision: Optional[str] = None
    vertical_negocio: Optional[str] = None
    descripcion_actividad: Optional[str] = None
    objetivos_generales: Optional[str] = None
    canales_comunicacion: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────
class ConfiguracionGlobalBase(BaseModel):
    clave: str = Field(..., max_length=100)
    valor: str = Field(..., max_length=500)
    tipo: str = Field("API")

class ConfiguracionGlobalCreate(ConfiguracionGlobalBase):
    empresa_id: int

class ConfiguracionGlobalResponse(ConfiguracionGlobalBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────
class AgenteBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    rol_prompt: Optional[str] = None
    status: Optional[int] = Field(0)
    tarea_actual: Optional[str] = None
    habilidades: Optional[str] = None      # JSON: [{nombre, descripcion}]
    objetivos: Optional[str] = None
    recursos: Optional[str] = None
    conocimientos: Optional[str] = None   # JSON: [titulo_nota]
    herramientas: Optional[str] = None    # JSON: [tool_id]
    modelo_config: Optional[str] = None
    skills_activos: Optional[str] = None  # JSON: ["search", ...]
    mcps_activos: Optional[str] = None    # JSON: ["mcp-filesystem", ...]
    permisos_api: Optional[str] = None    # JSON: {cred_id: [tools]}

class AgenteCreate(AgenteBase):
    empresa_id: int

class AgenteStatusUpdate(BaseModel):
    status: int
    tarea_actual: Optional[str] = None

class AgenteResponse(AgenteBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# ACTIVIDAD AGENTE
# ─────────────────────────────────────────
class ActividadAgenteBase(BaseModel):
    tipo: str = Field("tarea")        # tarea, cron, error, sistema
    titulo: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    estado: str = Field("completado") # completado, error, cancelado
    resultado: Optional[str] = None

class ActividadAgenteCreate(ActividadAgenteBase):
    pass

class ActividadAgenteResponse(ActividadAgenteBase):
    id: int
    agente_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# CRON PROGRAMADO
# ─────────────────────────────────────────
class CronProgramadoBase(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    expresion_cron: str = Field(..., max_length=100)
    activo: Optional[bool] = True

class CronProgramadoCreate(CronProgramadoBase):
    pass

class CronProgramadoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    expresion_cron: Optional[str] = None
    activo: Optional[bool] = None

class CronProgramadoResponse(CronProgramadoBase):
    id: int
    agente_id: int
    ultima_ejecucion: Optional[datetime] = None
    proxima_ejecucion: Optional[datetime] = None
    fecha_creacion: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# TAREA KANBAN
# ─────────────────────────────────────────
class TareaKanbanBase(BaseModel):
    titulo: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    estado: Optional[str] = Field("Pendiente")
    resultado_draft: Optional[str] = None

class TareaKanbanCreate(TareaKanbanBase):
    empresa_id: int
    agente_id: Optional[int] = None

class TareaKanbanUpdate(BaseModel):
    estado: str
    resultado_draft: Optional[str] = None

class TareaKanbanResponse(TareaKanbanBase):
    id: int
    empresa_id: int
    agente_id: Optional[int] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# LOG AUDITORÍA
# ─────────────────────────────────────────
class LogAuditoriaBase(BaseModel):
    mensaje: str

class LogAuditoriaCreate(LogAuditoriaBase):
    empresa_id: int
    agente_id: Optional[int] = None

class LogAuditoriaResponse(LogAuditoriaBase):
    id: int
    empresa_id: int
    agente_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardBroadcastPayload(BaseModel):
    type: str
    data: dict


# ─────────────────────────────────────────
# GRUPO
# ─────────────────────────────────────────
class GrupoBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    permisos: Optional[str] = None
    es_admin: Optional[bool] = False

class GrupoCreate(GrupoBase):
    pass

class GrupoResponse(GrupoBase):
    id: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# USUARIO
# ─────────────────────────────────────────
class UsuarioBase(BaseModel):
    username: str = Field(..., max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    activo: Optional[bool] = True
    grupo_id: Optional[int] = None
    canales_personales: Optional[str] = None  # JSON

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., max_length=100)

class UsuarioResponse(UsuarioBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    usuario: UsuarioResponse
    is_admin: bool


# ─────────────────────────────────────────
# NOTA
# ─────────────────────────────────────────
class NotaBase(BaseModel):
    titulo: str = Field(..., max_length=150)
    contenido: Optional[str] = None

class NotaCreate(NotaBase):
    empresa_id: int

class NotaResponse(NotaBase):
    id: int
    empresa_id: int
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# CREDENCIAL API
# ─────────────────────────────────────────
class CredencialApiBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    proveedor: str = Field(..., max_length=50)
    credencial_valor: str
    url_endpoint: Optional[str] = None
    config_json: Optional[str] = None
    activo: Optional[bool] = True
    permisos_herramientas: Optional[str] = None  # JSON

class CredencialApiCreate(CredencialApiBase):
    empresa_id: int

class CredencialApiResponse(CredencialApiBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True

class CredencialApiDetailResponse(CredencialApiBase):
    """Respuesta detallada — solo para admins muestra valor real."""
    id: int
    empresa_id: int
    valor_visible: str       # Valor real (admin) o '••••••••' (otros)
    permisos_herramientas: Optional[str] = None
    valor_snapshot: Optional[str] = None  # Solo admins

    class Config:
        from_attributes = True

class CredencialApiUpdate(BaseModel):
    nombre: Optional[str] = None
    credencial_valor: Optional[str] = None
    url_endpoint: Optional[str] = None
    config_json: Optional[str] = None
    activo: Optional[bool] = None
    permisos_herramientas: Optional[str] = None


# ─────────────────────────────────────────
# MENSAJE CHAT
# ─────────────────────────────────────────
class MensajeChatBase(BaseModel):
    remitente: str = Field(..., max_length=50)
    contenido: str

class MensajeChatCreate(MensajeChatBase):
    usuario_id: Optional[int] = None

class MensajeChatResponse(MensajeChatBase):
    id: int
    agente_id: int
    usuario_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True
