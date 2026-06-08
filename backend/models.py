import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, index=True, nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    # Datos básicos de empresa
    rif = Column(String(50), nullable=True)
    telefono = Column(String(50), nullable=True)
    direccion = Column(Text, nullable=True)
    pais = Column(String(100), nullable=True)
    sitio_web = Column(String(255), nullable=True)

    # Identidad corporativa
    mision = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    vertical_negocio = Column(String(100), nullable=True)
    descripcion_actividad = Column(Text, nullable=True)
    objetivos_generales = Column(Text, nullable=True)

    # Canales de comunicación (JSON)
    # Ej: {"telegram": {"bot_token": "...", "chat_id": "..."}, "email": {"smtp": "..."}}
    canales_comunicacion = Column(Text, nullable=True)

    configuraciones = relationship("ConfiguracionGlobal", back_populates="empresa", cascade="all, delete-orphan")
    agentes = relationship("Agente", back_populates="empresa", cascade="all, delete-orphan")
    tareas = relationship("TareaKanban", back_populates="empresa", cascade="all, delete-orphan")
    logs = relationship("LogAuditoria", back_populates="empresa", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="empresa", cascade="all, delete-orphan")
    credenciales = relationship("CredencialApi", back_populates="empresa", cascade="all, delete-orphan")


class ConfiguracionGlobal(Base):
    __tablename__ = "configuraciones_globales"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    clave = Column(String(100), nullable=False)
    valor = Column(String(500), nullable=False)
    tipo = Column(String(50), default="API")

    empresa = relationship("Empresa", back_populates="configuraciones")


class Agente(Base):
    __tablename__ = "agentes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)
    rol_prompt = Column(Text, nullable=True)
    status = Column(Integer, default=0)
    tarea_actual = Column(String(255), nullable=True)

    # Campos de identidad y capacidades
    habilidades = Column(Text, nullable=True)    # JSON: [{nombre, descripcion}]
    objetivos = Column(Text, nullable=True)      # Texto libre
    recursos = Column(Text, nullable=True)
    conocimientos = Column(Text, nullable=True)  # JSON: [titulo_nota]
    herramientas = Column(Text, nullable=True)   # JSON: [tool_id]
    modelo_config = Column(Text, nullable=True)  # JSON: {provider, model}

    # Skills / MCPs / APIs activados para este agente (JSON arrays de IDs/nombres)
    skills_activos = Column(Text, nullable=True)  # JSON: ["search", "memory", ...]
    mcps_activos = Column(Text, nullable=True)     # JSON: ["mcp-filesystem", ...]
    # Permisos de API a nivel agente (override del global)
    # JSON: {"credencial_id": [lista de tools permitidas]}
    permisos_api = Column(Text, nullable=True)

    empresa = relationship("Empresa", back_populates="agentes")
    tareas = relationship("TareaKanban", back_populates="agente", cascade="all, delete-orphan")
    logs = relationship("LogAuditoria", back_populates="agente", cascade="all, delete-orphan")
    mensajes = relationship("MensajeChat", back_populates="agente", cascade="all, delete-orphan")
    credenciales = relationship("CredencialApi", secondary="agente_credencial", back_populates="agentes")
    actividades = relationship("ActividadAgente", back_populates="agente", cascade="all, delete-orphan")
    crons = relationship("CronProgramado", back_populates="agente", cascade="all, delete-orphan")


class AgenteCredencial(Base):
    __tablename__ = "agente_credencial"

    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="CASCADE"), primary_key=True)
    credencial_id = Column(Integer, ForeignKey("credenciales_api.id", ondelete="CASCADE"), primary_key=True)


class CredencialApi(Base):
    __tablename__ = "credenciales_api"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)
    proveedor = Column(String(50), nullable=False)  # google, openrouter, openai, mcp_server, custom_skill, hermes
    credencial_valor = Column(Text, nullable=False)
    url_endpoint = Column(String(255), nullable=True)
    config_json = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)

    # Herramientas habilitadas para esta credencial (JSON)
    # Ej Google: ["gmail.read", "gmail.send", "drive.read", "drive.write", "sheets", "docs", "calendar",
    #             "ai_studio.gemini-1.5-flash", "ai_studio.gemini-1.5-pro", "ai_studio.imagen-3"]
    permisos_herramientas = Column(Text, nullable=True)

    # Snapshot para función revertir (guarda el valor previo antes de editar)
    valor_snapshot = Column(Text, nullable=True)

    empresa = relationship("Empresa", back_populates="credenciales")
    agentes = relationship("Agente", secondary="agente_credencial", back_populates="credenciales")


class ActividadAgente(Base):
    """Historial de actividades y tareas ejecutadas por un agente."""
    __tablename__ = "actividades_agente"

    id = Column(Integer, primary_key=True, index=True)
    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    tipo = Column(String(50), default="tarea")  # tarea, cron, error, sistema
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(50), default="completado")  # completado, error, cancelado
    resultado = Column(Text, nullable=True)

    agente = relationship("Agente", back_populates="actividades")


class CronProgramado(Base):
    """Crons programados para un agente."""
    __tablename__ = "crons_programados"

    id = Column(Integer, primary_key=True, index=True)
    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    expresion_cron = Column(String(100), nullable=False)  # Ej: "0 18 * * 5"
    activo = Column(Boolean, default=True)
    ultima_ejecucion = Column(DateTime, nullable=True)
    proxima_ejecucion = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    agente = relationship("Agente", back_populates="crons")


class MensajeChat(Base):
    __tablename__ = "mensajes_chat"

    id = Column(Integer, primary_key=True, index=True)
    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    remitente = Column(String(50), nullable=False)  # usuario, agente, sistema
    contenido = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    agente = relationship("Agente", back_populates="mensajes")
    usuario = relationship("Usuario")


class TareaKanban(Base):
    __tablename__ = "tareas_kanban"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="CASCADE"), nullable=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(50), default="Pendiente")
    resultado_draft = Column(Text, nullable=True)

    empresa = relationship("Empresa", back_populates="tareas")
    agente = relationship("Agente", back_populates="tareas")


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    agente_id = Column(Integer, ForeignKey("agentes.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    mensaje = Column(Text, nullable=False)

    empresa = relationship("Empresa", back_populates="logs")
    agente = relationship("Agente", back_populates="logs")


class Grupo(Base):
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, index=True, nullable=False)
    permisos = Column(Text, nullable=True)  # JSON: ["ver_credenciales", "editar_agentes", ...]
    es_admin = Column(Boolean, default=False)

    usuarios = relationship("Usuario", back_populates="grupo", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id", ondelete="SET NULL"), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    # Canal de comunicación personal del usuario (JSON)
    # Ej: {"telegram": {"chat_id": "..."}, "email": "user@example.com"}
    canales_personales = Column(Text, nullable=True)

    grupo = relationship("Grupo", back_populates="usuarios")


class Nota(Base):
    __tablename__ = "notas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(150), nullable=False)
    contenido = Column(Text, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    empresa = relationship("Empresa", back_populates="notas")
