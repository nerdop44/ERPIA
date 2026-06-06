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
