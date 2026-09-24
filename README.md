# PYMES - Ecosistema Integral de Gestión Empresarial

Repositorio principal (contenedor / paraguas) que centraliza los tres componentes de la solución PYMES mediante submódulos de Git:

```text
PYMES/
├── PYMES_BE/         -> Backend REST API (Python Flask, SQLAlchemy, JWT)
├── PYMES_FE/         -> Frontend Web (React / TypeScript / Vite)
└── pymesoft-movil/   -> Aplicación Móvil (Capacitor / Ionic / React / APK oficial)
```

---

## 📂 Submódulos Incluidos

| Repositorio | Descripción | Enlace al Repo Independiente |
| :--- | :--- | :--- |
| **PYMES_BE** | Backend, API RESTful, modelos, controladores y base de datos | [cristian1043/PYMES_BE](https://github.com/cristian1043/PYMES_BE) |
| **PYMES_FE** | Frontend Web para administración de escritorio | [cristian1043/PYMES_FE](https://github.com/cristian1043/PYMES_FE) |
| **pymesoft-movil** | Aplicación móvil híbrida optimizada para Android y Web | [cristian1043/PYMES_FE-movil](https://github.com/cristian1043/PYMES_FE-movil) |

---

## 🚀 Clonación del Proyecto Completo

Para clonar este repositorio contenedor junto con todo el código de los submódulos, ejecuta:

```bash
git clone --recurse-submodules https://github.com/cristian1043/PYMES.git
```

Si ya clonaste el proyecto sin la opción `--recurse-submodules`, inicializa los submódulos con:

```bash
git submodule update --init --recursive
```

---

## 🔄 Actualización de Submódulos

Para traer los últimos cambios de las ramas principales de cada submódulo:

```bash
git submodule update --remote --merge
```

---

## 🐳 Docker Compose

Para levantar los entornos con Docker:

```bash
docker compose up --build
```
