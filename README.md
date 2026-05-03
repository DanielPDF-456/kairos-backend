# KAIROS Backend

Sistema de prevención de errores de administración de medicamentos.

## Requisitos

- Python 3.12.10
- PostgreSQL 12+
- pip o poetry para gestión de dependencias

## Instalación

### 1. Configurar el entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tus valores
```

### 4. Configurar Base de datos en Render

#### Opción A: Usar PostgreSQL en Render (Recomendado para Producción)

1. Ir a https://render.com/
2. Crear una cuenta gratuita
3. Ir a "Databases"
4. Click en "New +"
5. Seleccionar "PostgreSQL"
6. Configurar:
   - Name: `kairos-db`
   - Region: Tu región más cercana
   - PostgreSQL Version: 12 o superior
   - Database: `kairos_db`
   
7. Copiar la "Internal Database URL"
8. Pegar en el archivo `.env` en la variable `DATABASE_URL`

#### Opción B: Usar PostgreSQL Local (Para Desarrollo)

```bash
# Instalar PostgreSQL desde https://www.postgresql.org/download/

# Crear base de datos
createdb kairos_db

# En .env:
DATABASE_URL=postgresql://postgres:password@localhost:5432/kairos_db
```

### 5. Inicializar la base de datos

```bash
python app.py
```

La base de datos se creará automáticamente con las tablas necesarias.

## Estructura del Proyecto

```
backend/
├── app.py                 # Aplicación Flask principal
├── requirements.txt       # Dependencias de Python
├── .env.example          # Ejemplo de configuración
├── README.md             # Este archivo
└── .gitignore            # Archivos a ignorar en Git
```

## API Endpoints

### Autenticación
- `POST /api/auth/registro` - Registrar usuario
- `POST /api/auth/login` - Iniciar sesión

### Pacientes
- `GET /api/pacientes` - Obtener todos los pacientes
- `POST /api/pacientes` - Crear paciente
- `GET /api/pacientes/<id>` - Obtener detalles del paciente

### Medicamentos
- `GET /api/medicamentos` - Obtener medicamentos
- `POST /api/medicamentos` - Crear medicamento (admin)

### Prescripciones
- `GET /api/prescripciones` - Obtener prescripciones
- `POST /api/prescripciones` - Crear prescripción

### Administraciones
- `GET /api/administraciones/pendientes` - Obtener administraciones pendientes
- `POST /api/administraciones` - Registrar administración

### Reportes
- `GET /api/reportes/errores-horario` - Reporte de errores
- `GET /api/reportes/desempeño-turno` - Reporte de desempeño

### Sistema
- `GET /api/health` - Health check
- `GET /` - Información de la API

## Desarrollo

Para ejecutar en modo desarrollo:

```bash
set FLASK_DEBUG=True
python app.py
```

## Autenticación

La API usa JWT (JSON Web Tokens). Después de hacer login:

```bash
curl -X GET http://localhost:5000/api/pacientes \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Roles de Usuario

- `medico` - Puede crear pacientes y prescripciones
- `enfermera` - Puede registrar administraciones de medicamentos
- `admin` - Acceso total al sistema

## Seguridad

⚠️ **IMPORTANTE PARA PRODUCCIÓN:**

1. Cambiar `SECRET_KEY` en `.env` a una clave fuerte
2. Usar HTTPS en la URL de la base de datos
3. Configurar CORS apropiadamente
4. Usar variables de entorno para secretos
5. Implementar rate limiting
6. Agregar validación adicional de entrada

## Integración con Render

### Desplegar en Render

1. Conectar repositorio GitHub
2. Crear nuevo "Web Service"
3. Configurar:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Agregar variables de entorno en Render dashboard
5. Conectar base de datos PostgreSQL de Render

## Troubleshooting

### Error de conexión a base de datos

```
Verifica que:
1. PostgreSQL está corriendo
2. DATABASE_URL es correcta
3. Base de datos existe
4. Usuario y contraseña son correctos
```

### Error de módulo no encontrado

```bash
pip install -r requirements.txt --upgrade
```

## Contacto y Soporte

Para issues o preguntas, contacta al equipo de desarrollo.

## Licencia

Confidencial - Sistema Kairos 2026
