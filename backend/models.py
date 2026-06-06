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

    configuraciones = relationship("ConfiguracionGlobal", back_populates="empresa", cascade="all, delete-orphan")
    agentes = relationship("Agente", back_populates="empresa", cascade="all, delete-orphan")
    tareas = relationship("TareaKanban", back_populates="empresa", cascade="all, delete-orphan")
    logs = relationship("LogAuditoria", back_populates="empresa", cascade="all, delete-orphan")
    notas = relationship("Nota", back_populates="empresa", cascade="all, delete-orphan")


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

    empresa = relationship("Empresa", back_populates="agentes")
    tareas = relationship("TareaKanban", back_populates="agente", cascade="all, delete-orphan")
    logs = relationship("LogAuditoria", back_populates="agente", cascade="all, delete-orphan")


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
    permisos = Column(Text, nullable=True)  # Lista en formato JSON

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

    grupo = relationship("Grupo", back_populates="usuarios")


class Nota(Base):
    __tablename__ = "notas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String(150), nullable=False)
    contenido = Column(Text, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    empresa = relationship("Empresa", back_populates="notas")
