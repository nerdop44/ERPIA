from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

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


class AgenteBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    rol_prompt: Optional[str] = None
    status: Optional[int] = Field(0)
    tarea_actual: Optional[str] = None
    habilidades: Optional[str] = None
    objetivos: Optional[str] = None
    recursos: Optional[str] = None
    conocimientos: Optional[str] = None
    herramientas: Optional[str] = None
    modelo_config: Optional[str] = None

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


class GrupoBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    permisos: Optional[str] = None

class GrupoCreate(GrupoBase):
    pass

class GrupoResponse(GrupoBase):
    id: int

    class Config:
        from_attributes = True


class UsuarioBase(BaseModel):
    username: str = Field(..., max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    activo: Optional[bool] = True
    grupo_id: Optional[int] = None

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


class CredencialApiBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    proveedor: str = Field(..., max_length=50)
    credencial_valor: str
    url_endpoint: Optional[str] = None
    config_json: Optional[str] = None
    activo: Optional[bool] = True

class CredencialApiCreate(CredencialApiBase):
    empresa_id: int

class CredencialApiResponse(CredencialApiBase):
    id: int
    empresa_id: int

    class Config:
        from_attributes = True


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

