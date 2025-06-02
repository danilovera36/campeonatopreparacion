# Campeonato Preparación Sub-15 - Liga Rosarina

Sistema de gestión para el campeonato de preparación sub-15 de la Liga Rosarina.

## Características

- Gestión de partidos y resultados
- Tabla de posiciones automática
- Control de goleadores
- Sistema de semifinales y final
- Panel de administración
- Sistema de respaldo automático

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd preparacion
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
Crear un archivo `.env` en la raíz del proyecto con:
```
SECRET_KEY=tu_clave_secreta
ADMIN_USER=tu_usuario
ADMIN_PASS=tu_contraseña
FLASK_DEBUG=False
```

## Uso

1. Iniciar el servidor:
```bash
python app.py
```

2. Acceder a la aplicación:
- Abrir un navegador y visitar `http://localhost:5000`
- Para acceder al panel de administración, hacer clic en "Admin" y usar las credenciales configuradas

## Estructura de archivos

```
preparacion/
├── app.py              # Aplicación principal
├── requirements.txt    # Dependencias
├── README.md          # Este archivo
├── .env              # Variables de entorno (no incluido en el repo)
├── backups/          # Directorio de respaldos
├── static/           # Archivos estáticos
│   └── images/      # Imágenes y escudos
└── templates/        # Plantillas HTML
    ├── base.html
    ├── index.html
    └── ...
```

## Seguridad

- Las credenciales de administrador se almacenan en variables de entorno
- Sistema de respaldo automático antes de cada modificación
- Protección contra acceso no autorizado
- Logging de todas las operaciones importantes

## Mantenimiento

- Los logs se almacenan en `app.log`
- Los respaldos se guardan en el directorio `backups/`
- Se recomienda hacer respaldos periódicos del directorio completo

## Soporte

Para reportar problemas o sugerir mejoras, por favor crear un issue en el repositorio. 