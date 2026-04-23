# 🎬 CinemaCare Pro — Guía de Instalación

## Estructura del Proyecto

```
cinemacarpro/
├── app.py                  ← Backend Flask (rutas, API, base de datos)
├── requirements.txt        ← Dependencias Python
├── static/
│   └── uploads/            ← Fotos de evidencia (se crea automáticamente)
└── templates/
    ├── index.html          ← App principal (diagnóstico paso a paso)
    └── admin.html          ← Panel de administración de incidentes
```

## Instalación y Ejecución

```bash
# 1. Crea un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Ejecuta la aplicación
python app.py
```

## Accede a la aplicación

- **App de diagnóstico:** http://localhost:5000
- **Panel de administración:** http://localhost:5000/admin

## API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | App principal de diagnóstico |
| GET | `/admin` | Panel de administración |
| GET | `/api/errors` | Lista todos los códigos de error |
| GET | `/api/error/<code>` | Pasos de un error específico |
| POST | `/api/resolve` | Registra un incidente resuelto |
| POST | `/api/escalate` | Registra un escalamiento a senior |
| GET | `/api/incidents` | Lista todos los incidentes (JSON) |

## Códigos de Error Incluidos

| Código | Descripción | Categoría |
|--------|-------------|-----------|
| E001 | Imagen Distorsionada / Artefactos Visuales | Proyección |
| E002 | Sin Audio / Audio Intermitente | Audio |
| E003 | Proyector No Enciende | Proyección |
| E004 | Pantalla Negra / Sin Señal | Proyección |
| E005 | Error de Certificado KDM | Software |

## Para Producción

Reemplaza la base de datos en memoria `incidents_db = []` con:
- **SQLite** (simple, un archivo): `pip install flask-sqlalchemy`
- **PostgreSQL** (múltiples cines): `pip install psycopg2`

Para notificaciones de escalamiento, agrega en `escalate_incident()`:
- Email: `pip install flask-mail`
- SMS: Twilio API
- WhatsApp: Twilio/Meta Business API