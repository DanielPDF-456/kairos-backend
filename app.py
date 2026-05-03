"""
KAIROS - Sistema Integrado de Prevención de Errores de Horario Administrativo
Backend Flask con SQLAlchemy y PostgreSQL en Render
"""

import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, String, Integer, Float, Boolean, Text, Enum, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de base de datos para Render
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/kairos_db')

# Render usa postgresql:// pero SQLAlchemy necesita postgresql+psycopg2://
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)

# Configuración de la aplicación
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'kairos-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# Inicializar extensiones
db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ==================== MODELOS DE BASE DE DATOS ====================

class Usuario(db.Model):
    """Modelo para usuarios (médicos, enfermeras, administradores)"""
    __tablename__ = 'usuarios'
    
    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(120), unique=True, nullable=False)
    password = db.Column(String(255), nullable=False)
    nombre = db.Column(String(120), nullable=False)
    apellido = db.Column(String(120), nullable=False)
    rol = db.Column(String(50), nullable=False)  # medico, enfermera, admin
    cédula = db.Column(String(20), unique=True, nullable=False)
    turno = db.Column(String(50), nullable=True)  # matutino, vespertino, nocturno
    departamento = db.Column(String(120), nullable=True)
    activo = db.Column(Boolean, default=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    pacientes = relationship('Paciente', back_populates='medico_asignado')
    administraciones = relationship('Administracion', back_populates='usuario')
    logs_auditoria = relationship('LogAuditoria', back_populates='usuario')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'rol': self.rol,
            'cédula': self.cédula,
            'turno': self.turno,
            'departamento': self.departamento,
            'activo': self.activo
        }


class Paciente(db.Model):
    """Modelo para pacientes"""
    __tablename__ = 'pacientes'
    
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(String(120), nullable=False)
    apellido = db.Column(String(120), nullable=False)
    cedula = db.Column(String(20), unique=True, nullable=False)
    edad = db.Column(Integer, nullable=False)
    sexo = db.Column(String(10), nullable=False)  # M, F, O
    habitacion = db.Column(String(20), nullable=True)
    cama = db.Column(String(20), nullable=True)
    diagnostico = db.Column(Text, nullable=True)
    alergias = db.Column(Text, nullable=True)
    medico_id = db.Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    estado = db.Column(String(50), default='activo')  # activo, alta, fallecido
    fecha_ingreso = db.Column(DateTime, default=datetime.utcnow)
    fecha_alta = db.Column(DateTime, nullable=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    medico_asignado = relationship('Usuario', back_populates='pacientes')
    prescripciones = relationship('Prescripcion', back_populates='paciente', cascade='all, delete-orphan')
    administraciones = relationship('Administracion', back_populates='paciente', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'cedula': self.cedula,
            'edad': self.edad,
            'sexo': self.sexo,
            'habitacion': self.habitacion,
            'cama': self.cama,
            'diagnostico': self.diagnostico,
            'alergias': self.alergias,
            'medico_id': self.medico_id,
            'estado': self.estado,
            'fecha_ingreso': self.fecha_ingreso.isoformat() if self.fecha_ingreso else None
        }


class Medicamento(db.Model):
    """Modelo para medicamentos"""
    __tablename__ = 'medicamentos'
    
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(String(120), unique=True, nullable=False)
    dosis_standar = db.Column(String(100), nullable=True)
    concentracion = db.Column(String(100), nullable=True)
    via_administracion = db.Column(String(50), nullable=False)  # oral, IV, IM, etc
    efectos_secundarios = db.Column(Text, nullable=True)
    contraindicaciones = db.Column(Text, nullable=True)
    critico = db.Column(Boolean, default=False)  # Indicador de medicamento crítico
    requiere_verificacion = db.Column(Boolean, default=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    prescripciones = relationship('Prescripcion', back_populates='medicamento')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'dosis_standar': self.dosis_standar,
            'concentracion': self.concentracion,
            'via_administracion': self.via_administracion,
            'critico': self.critico,
            'requiere_verificacion': self.requiere_verificacion
        }


class Prescripcion(db.Model):
    """Modelo para prescripciones médicas"""
    __tablename__ = 'prescripciones'
    
    id = db.Column(Integer, primary_key=True)
    paciente_id = db.Column(Integer, ForeignKey('pacientes.id'), nullable=False)
    medicamento_id = db.Column(Integer, ForeignKey('medicamentos.id'), nullable=False)
    dosis = db.Column(String(100), nullable=False)
    frecuencia = db.Column(String(100), nullable=False)  # cada 6h, cada 8h, etc
    horarios = db.Column(String(500), nullable=False)  # JSON: ["06:00", "12:00", "18:00", "00:00"]
    fecha_inicio = db.Column(DateTime, nullable=False)
    fecha_fin = db.Column(DateTime, nullable=True)
    motivo = db.Column(Text, nullable=True)
    notas_adicionales = db.Column(Text, nullable=True)
    activa = db.Column(Boolean, default=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    paciente = relationship('Paciente', back_populates='prescripciones')
    medicamento = relationship('Medicamento', back_populates='prescripciones')
    administraciones = relationship('Administracion', back_populates='prescripcion', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'paciente_id': self.paciente_id,
            'medicamento_id': self.medicamento_id,
            'dosis': self.dosis,
            'frecuencia': self.frecuencia,
            'horarios': self.horarios,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'motivo': self.motivo,
            'activa': self.activa
        }


class Administracion(db.Model):
    """Modelo para registro de administración de medicamentos"""
    __tablename__ = 'administraciones'
    
    id = db.Column(Integer, primary_key=True)
    prescripcion_id = db.Column(Integer, ForeignKey('prescripciones.id'), nullable=False)
    paciente_id = db.Column(Integer, ForeignKey('pacientes.id'), nullable=False)
    usuario_id = db.Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    hora_programada = db.Column(DateTime, nullable=False)
    hora_administrada = db.Column(DateTime, nullable=True)
    estado = db.Column(String(50), default='pendiente')  # pendiente, administrado, rechazado, perdido
    retraso_minutos = db.Column(Integer, nullable=True)
    codigo_verificacion_paciente = db.Column(String(50), nullable=True)
    codigo_verificacion_medicamento = db.Column(String(50), nullable=True)
    observaciones = db.Column(Text, nullable=True)
    reaccion_adversa = db.Column(Boolean, default=False)
    descripcion_reaccion = db.Column(Text, nullable=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    prescripcion = relationship('Prescripcion', back_populates='administraciones')
    paciente = relationship('Paciente', back_populates='administraciones')
    usuario = relationship('Usuario', back_populates='administraciones')
    
    def to_dict(self):
        return {
            'id': self.id,
            'prescripcion_id': self.prescripcion_id,
            'paciente_id': self.paciente_id,
            'usuario_id': self.usuario_id,
            'hora_programada': self.hora_programada.isoformat() if self.hora_programada else None,
            'hora_administrada': self.hora_administrada.isoformat() if self.hora_administrada else None,
            'estado': self.estado,
            'retraso_minutos': self.retraso_minutos,
            'reaccion_adversa': self.reaccion_adversa
        }


class LogAuditoria(db.Model):
    """Modelo para registro de auditoría del sistema"""
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(Integer, primary_key=True)
    usuario_id = db.Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    tipo_evento = db.Column(String(100), nullable=False)  # login, crear_prescripcion, administrar_medicamento, etc
    descripcion = db.Column(Text, nullable=False)
    ip_address = db.Column(String(50), nullable=True)
    tabla_afectada = db.Column(String(100), nullable=True)
    registro_id = db.Column(Integer, nullable=True)
    fecha_creacion = db.Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    usuario = relationship('Usuario', back_populates='logs_auditoria')
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'tipo_evento': self.tipo_evento,
            'descripcion': self.descripcion,
            'tabla_afectada': self.tabla_afectada,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }


# ==================== DECORADORES ====================

def token_required(f):
    """Decorador para verificar token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'mensaje': 'Token inválido'}), 401
        
        if not token:
            return jsonify({'mensaje': 'Token requerido'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            usuario = Usuario.query.get(data['usuario_id'])
            if not usuario:
                return jsonify({'mensaje': 'Usuario no encontrado'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'mensaje': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'mensaje': 'Token inválido'}), 401
        
        return f(usuario, *args, **kwargs)
    
    return decorated


def rol_required(roles):
    """Decorador para verificar roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(usuario, *args, **kwargs):
            if usuario.rol not in roles:
                return jsonify({'mensaje': 'Acceso denegado'}), 403
            return f(usuario, *args, **kwargs)
        return decorated_function
    return decorator


# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/api/auth/registro', methods=['POST'])
def registro():
    """Registrar nuevo usuario"""
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        campos_requeridos = ['email', 'password', 'nombre', 'apellido', 'rol', 'cedula']
        if not all(campo in data for campo in campos_requeridos):
            return jsonify({'error': 'Campos requeridos faltantes'}), 400
        
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email ya registrado'}), 400
        
        if Usuario.query.filter_by(cédula=data['cedula']).first():
            return jsonify({'error': 'Cédula ya registrada'}), 400
        
        # Crear nuevo usuario
        usuario = Usuario(
            email=data['email'],
            nombre=data['nombre'],
            apellido=data['apellido'],
            rol=data['rol'],
            cédula=data['cedula'],
            turno=data.get('turno'),
            departamento=data.get('departamento')
        )
        usuario.set_password(data['password'])
        
        db.session.add(usuario)
        db.session.commit()
        
        # Registrar en auditoría
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='registro',
            descripcion=f'Usuario {usuario.email} registrado exitosamente',
            tabla_afectada='usuarios',
            registro_id=usuario.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'mensaje': 'Usuario registrado exitosamente', 'usuario_id': usuario.id}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Iniciar sesión"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email y contraseña requeridos'}), 400
        
        usuario = Usuario.query.filter_by(email=data['email']).first()
        
        if not usuario or not usuario.check_password(data['password']):
            return jsonify({'error': 'Email o contraseña incorrectos'}), 401
        
        if not usuario.activo:
            return jsonify({'error': 'Usuario inactivo'}), 401
        
        # Generar token JWT
        token = jwt.encode(
            {
                'usuario_id': usuario.id,
                'email': usuario.email,
                'rol': usuario.rol,
                'exp': datetime.utcnow() + timedelta(hours=24)
            },
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        # Registrar en auditoría
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='login',
            descripcion=f'Usuario {usuario.email} inició sesión',
            tabla_afectada='usuarios',
            registro_id=usuario.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'mensaje': 'Inicio de sesión exitoso',
            'token': token,
            'usuario': usuario.to_dict()
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE PACIENTES ====================

@app.route('/api/pacientes', methods=['GET'])
@token_required
def obtener_pacientes(usuario):
    """Obtener lista de pacientes"""
    try:
        pacientes = Paciente.query.all()
        return jsonify([p.to_dict() for p in pacientes]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pacientes', methods=['POST'])
@token_required
@rol_required(['medico', 'admin'])
def crear_paciente(usuario):
    """Crear nuevo paciente"""
    try:
        data = request.get_json()
        
        campos_requeridos = ['nombre', 'apellido', 'cedula', 'edad', 'sexo']
        if not all(campo in data for campo in campos_requeridos):
            return jsonify({'error': 'Campos requeridos faltantes'}), 400
        
        if Paciente.query.filter_by(cedula=data['cedula']).first():
            return jsonify({'error': 'Cédula ya registrada'}), 400
        
        paciente = Paciente(
            nombre=data['nombre'],
            apellido=data['apellido'],
            cedula=data['cedula'],
            edad=data['edad'],
            sexo=data['sexo'],
            habitacion=data.get('habitacion'),
            cama=data.get('cama'),
            diagnostico=data.get('diagnostico'),
            alergias=data.get('alergias'),
            medico_id=usuario.id
        )
        
        db.session.add(paciente)
        db.session.commit()
        
        # Registrar en auditoría
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='crear_paciente',
            descripcion=f'Paciente {paciente.nombre} {paciente.apellido} creado',
            tabla_afectada='pacientes',
            registro_id=paciente.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'mensaje': 'Paciente creado exitosamente', 'paciente': paciente.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/pacientes/<int:id>', methods=['GET'])
@token_required
def obtener_paciente(usuario, id):
    """Obtener detalles de un paciente"""
    try:
        paciente = Paciente.query.get(id)
        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404
        
        return jsonify(paciente.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/pacientes/<int:id>/alta', methods=['PUT'])
@token_required
@rol_required(['medico', 'admin'])
def dar_alta_paciente(usuario, id):
    """Dar de alta a un paciente"""
    try:
        paciente = Paciente.query.get(id)
        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404

        paciente.estado = 'alta'
        db.session.commit()

        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='alta_paciente',
            descripcion=f'Paciente {paciente.nombre} {paciente.apellido} dado de alta',
            tabla_afectada='pacientes',
            registro_id=paciente.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'mensaje': 'Paciente dado de alta', 'paciente': paciente.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/pacientes/<int:id>', methods=['DELETE'])
@token_required
@rol_required(['medico', 'admin'])
def eliminar_paciente(usuario, id):
    """Eliminar paciente"""
    try:
        paciente = Paciente.query.get(id)
        if not paciente:
            return jsonify({'error': 'Paciente no encontrado'}), 404
        
        db.session.delete(paciente)
        db.session.commit()
        
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='eliminar_paciente',
            descripcion=f'Paciente {paciente.nombre} {paciente.apellido} eliminado',
            tabla_afectada='pacientes',
            registro_id=id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'mensaje': 'Paciente eliminado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE MEDICAMENTOS ====================

@app.route('/api/medicamentos', methods=['GET'])
@token_required
def obtener_medicamentos(usuario):
    """Obtener lista de medicamentos"""
    try:
        medicamentos = Medicamento.query.all()
        return jsonify([m.to_dict() for m in medicamentos]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/medicamentos', methods=['POST'])
@token_required
@rol_required(['admin'])
def crear_medicamento(usuario):
    """Crear nuevo medicamento"""
    try:
        data = request.get_json()
        
        campos_requeridos = ['nombre', 'via_administracion']
        if not all(campo in data for campo in campos_requeridos):
            return jsonify({'error': 'Campos requeridos faltantes'}), 400
        
        medicamento = Medicamento(
            nombre=data['nombre'],
            dosis_standar=data.get('dosis_standar'),
            concentracion=data.get('concentracion'),
            via_administracion=data['via_administracion'],
            efectos_secundarios=data.get('efectos_secundarios'),
            contraindicaciones=data.get('contraindicaciones'),
            critico=data.get('critico', False)
        )
        
        db.session.add(medicamento)
        db.session.commit()
        
        return jsonify({'mensaje': 'Medicamento creado', 'medicamento': medicamento.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/prescripciones/<int:id>', methods=['DELETE'])
@token_required
@rol_required(['medico', 'admin'])
def cancelar_prescripcion(usuario, id):
    """Cancelar/desactivar una prescripción"""
    try:
        prescripcion = Prescripcion.query.get(id)
        if not prescripcion:
            return jsonify({'error': 'Prescripción no encontrada'}), 404

        prescripcion.activa = False
        db.session.commit()

        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='cancelar_prescripcion',
            descripcion=f'Prescripción #{id} cancelada',
            tabla_afectada='prescripciones',
            registro_id=id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'mensaje': 'Prescripción cancelada correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE PRESCRIPCIONES ====================

@app.route('/api/prescripciones', methods=['GET'])
@token_required
def obtener_prescripciones(usuario):
    """Obtener prescripciones activas"""
    try:
        prescripciones = Prescripcion.query.filter_by(activa=True).all()
        return jsonify([p.to_dict() for p in prescripciones]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/prescripciones', methods=['POST'])
@token_required
@rol_required(['medico', 'admin'])
def crear_prescripcion(usuario):
    """Crear nueva prescripción"""
    try:
        data = request.get_json()
        
        campos_requeridos = ['paciente_id', 'medicamento_id', 'dosis', 'frecuencia', 'horarios', 'fecha_inicio']
        if not all(campo in data for campo in campos_requeridos):
            return jsonify({'error': 'Campos requeridos faltantes'}), 400
        
        prescripcion = Prescripcion(
            paciente_id=data['paciente_id'],
            medicamento_id=data['medicamento_id'],
            dosis=data['dosis'],
            frecuencia=data['frecuencia'],
            horarios=data['horarios'],
            fecha_inicio=datetime.fromisoformat(data['fecha_inicio']),
            fecha_fin=datetime.fromisoformat(data['fecha_fin']) if data.get('fecha_fin') else None,
            motivo=data.get('motivo'),
            notas_adicionales=data.get('notas_adicionales')
        )
        
        db.session.add(prescripcion)
        db.session.commit()
        
        # Registrar en auditoría
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='crear_prescripcion',
            descripcion=f'Prescripción creada para paciente {data["paciente_id"]}',
            tabla_afectada='prescripciones',
            registro_id=prescripcion.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'mensaje': 'Prescripción creada', 'prescripcion': prescripcion.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE ADMINISTRACIÓN ====================

@app.route('/api/administraciones/pendientes', methods=['GET'])
@token_required
def obtener_administraciones_pendientes(usuario):
    """Obtener administraciones pendientes"""
    try:
        ahora = datetime.utcnow()
        hace_30_min = ahora - timedelta(minutes=30)
        
        # Pendientes
        pendientes = Administracion.query.filter(
            Administracion.estado == 'pendiente',
            Administracion.hora_programada <= ahora
        ).all()
        
        # Retrasadas (más de 30 minutos)
        retrasadas = Administracion.query.filter(
            Administracion.estado == 'pendiente',
            Administracion.hora_programada < hace_30_min
        ).all()
        
        resultado = {
            'pendientes': [a.to_dict() for a in pendientes],
            'retrasadas': [a.to_dict() for a in retrasadas],
            'total_criticas': len(retrasadas)
        }
        
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/administraciones', methods=['POST'])
@token_required
@rol_required(['enfermera', 'admin'])
def registrar_administracion(usuario):
    """Registrar administración de medicamento"""
    try:
        data = request.get_json()
        
        campos_requeridos = ['prescripcion_id', 'paciente_id', 'codigo_verificacion_paciente']
        if not all(campo in data for campo in campos_requeridos):
            return jsonify({'error': 'Campos requeridos faltantes'}), 400
        
        prescripcion = Prescripcion.query.get(data['prescripcion_id'])
        if not prescripcion:
            return jsonify({'error': 'Prescripción no encontrada'}), 404
        
        administracion = Administracion.query.filter_by(
            prescripcion_id=data['prescripcion_id'],
            estado='pendiente'
        ).first()
        
        if not administracion:
            return jsonify({'error': 'No hay administración pendiente para esta prescripción'}), 404
        
        # Calcular retraso
        ahora = datetime.utcnow()
        retraso = int((ahora - administracion.hora_programada).total_seconds() / 60)
        
        administracion.hora_administrada = ahora
        administracion.usuario_id = usuario.id
        administracion.retraso_minutos = retraso
        administracion.codigo_verificacion_paciente = data['codigo_verificacion_paciente']
        administracion.codigo_verificacion_medicamento = data.get('codigo_verificacion_medicamento')
        administracion.observaciones = data.get('observaciones')
        
        # Definir estado basado en el retraso
        if retraso <= 30:
            administracion.estado = 'administrado'
        else:
            administracion.estado = 'administrado'  # Registrar igual pero con retraso crítico
        
        db.session.commit()
        
        # Registrar en auditoría
        log = LogAuditoria(
            usuario_id=usuario.id,
            tipo_evento='administrar_medicamento',
            descripcion=f'Medicamento administrado con retraso de {retraso} minutos',
            tabla_afectada='administraciones',
            registro_id=administracion.id,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'mensaje': 'Administración registrada', 'administracion': administracion.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/administraciones/generar', methods=['POST'])
@token_required
@rol_required(['admin', 'medico'])
def generar_administraciones(usuario):
    """Generar administraciones del día a partir de prescripciones activas"""
    try:
        from datetime import date
        hoy = date.today()
        prescripciones = Prescripcion.query.filter_by(activa=True).all()
        generadas = 0

        for presc in prescripciones:
            try:
                horarios = json.loads(presc.horarios)
            except Exception:
                horarios = [presc.horarios]

            for horario in horarios:
                try:
                    hora, minuto = map(int, horario.split(':'))
                    hora_programada = datetime(hoy.year, hoy.month, hoy.day, hora, minuto)

                    # Verificar si ya existe una administración para este horario hoy
                    existe = Administracion.query.filter_by(
                        prescripcion_id=presc.id,
                        hora_programada=hora_programada
                    ).first()

                    if not existe:
                        admin = Administracion(
                            prescripcion_id=presc.id,
                            paciente_id=presc.paciente_id,
                            usuario_id=usuario.id,
                            hora_programada=hora_programada,
                            estado='pendiente'
                        )
                        db.session.add(admin)
                        generadas += 1
                except Exception:
                    continue

        db.session.commit()
        return jsonify({
            'mensaje': f'{generadas} administraciones generadas para hoy',
            'generadas': generadas
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ==================== RUTAS DE REPORTES Y ANÁLISIS ====================

@app.route('/api/reportes/errores-horario', methods=['GET'])
@token_required
@rol_required(['admin', 'medico'])
def reporte_errores_horario(usuario):
    """Reporte de errores de horario administrativo"""
    try:
        # Últimos 30 días
        hace_30_dias = datetime.utcnow() - timedelta(days=30)
        
        administraciones = Administracion.query.filter(
            Administracion.fecha_creacion >= hace_30_dias
        ).all()
        
        total = len(administraciones)
        retrasadas = len([a for a in administraciones if a.retraso_minutos and a.retraso_minutos > 30])
        con_reaccion = len([a for a in administraciones if a.reaccion_adversa])
        
        desempeño = {
            'total_administraciones': total,
            'retrasadas_mas_30min': retrasadas,
            'porcentaje_puntualidad': ((total - retrasadas) / total * 100) if total > 0 else 0,
            'reacciones_adversas': con_reaccion,
            'periodo': '30 días'
        }
        
        return jsonify(desempeño), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reportes/desempeño-turno', methods=['GET'])
@token_required
@rol_required(['admin'])
def reporte_desempeño_turno(usuario):
    """Reporte de desempeño por turno"""
    try:
        hace_30_dias = datetime.utcnow() - timedelta(days=30)
        
        usuarios = Usuario.query.filter(Usuario.turno != None).all()
        
        resultado = []
        for u in usuarios:
            admin_count = Administracion.query.filter(
                Administracion.usuario_id == u.id,
                Administracion.fecha_creacion >= hace_30_dias
            ).count()
            
            retrasadas_count = Administracion.query.filter(
                Administracion.usuario_id == u.id,
                Administracion.retraso_minutos > 30,
                Administracion.fecha_creacion >= hace_30_dias
            ).count()
            
            resultado.append({
                'usuario': u.to_dict(),
                'total_administraciones': admin_count,
                'retrasadas': retrasadas_count,
                'puntualidad': ((admin_count - retrasadas_count) / admin_count * 100) if admin_count > 0 else 0
            })
        
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE LOGS Y AUDITORÍA ====================

@app.route('/api/logs-auditoria', methods=['GET'])
@token_required
@rol_required(['admin'])
def obtener_logs_auditoria(usuario):
    """Obtener logs de auditoría"""
    try:
        logs = LogAuditoria.query.order_by(LogAuditoria.fecha_creacion.desc()).limit(100).all()
        return jsonify([log.to_dict() for log in logs]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RUTAS DE SALUD ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verificar salud de la API"""
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'healthy', 'message': 'API Kairos funcionando correctamente'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'message': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Ruta raíz"""
    return jsonify({
        'aplicacion': 'KAIROS',
        'version': '1.0.0',
        'descripcion': 'Sistema Integrado de Prevención de Errores de Horario Administrativo',
        'documentacion': '/api/health'
    }), 200


# ==================== MANEJADOR DE ERRORES ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ruta no encontrada'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Error interno del servidor'}), 500


# ==================== INICIALIZACIÓN ====================

def init_db():
    """Inicializar base de datos"""
    with app.app_context():
        db.create_all()
        print("✓ Base de datos inicializada")

# Esto crea las tablas siempre, sin importar cómo arranque el servidor
init_db()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)
