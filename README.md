
### 1.4 Guardar
- Abajo escribe mensaje: `Add professional README with badges and documentation`
- Haz clic en **"Commit new file"**

---

## 📍 PASO 2: Crear README para el frontend

### 2.1 Ir a tu repositorio frontend
Ve a `https://github.com/Tonystylex17-09/americafitness-mobile`

### 2.2 Crear archivo README.md
1. Haz clic en **"Add file"** → **"Create new file"**
2. Nombra el archivo: `README.md`

### 2.3 Copiar y pegar este contenido:

```markdown
# AméricaFitness - App Móvil

[![Flutter](https://img.shields.io/badge/Flutter-3.29-blue)](https://flutter.dev)
[![Dart](https://img.shields.io/badge/Dart-3.11-lightblue)](https://dart.dev)
[![Platform](https://img.shields.io/badge/Platform-iOS%20%7C%20Android%20%7C%20Web-green)](https://flutter.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

App móvil de gimnasio profesional desarrollada con **Flutter**. Incluye gamificación, nutrición, mapa, check-in con QR, tienda y más.

## 📱 Características

- ✅ **13 pantallas funcionales**
- ✅ Sistema de gamificación (puntos, streaks, insignias, ranking, desafíos semanales)
- ✅ Check-in con QR + streak de días
- ✅ Tienda con carrito de compras
- ✅ Nutrición con cálculo de IMC y planes de comida personalizados
- ✅ Mapa de sedes con Google Maps
- ✅ Notificaciones push (Firebase)
- ✅ Historial de pedidos
- ✅ Rutinas de entrenamiento con días infinitos
- ✅ Diseño dark/red profesional
- ✅ Onboarding interactivo

## 📸 Capturas de Pantalla

| Login | Home | Tienda | Nutrición |
|-------|------|--------|-----------|
| (inserte imagen) | (inserte imagen) | (inserte imagen) | (inserte imagen) |

| Asistencia | Ranking | Insignias | Mapa |
|------------|---------|-----------|------|
| (inserte imagen) | (inserte imagen) | (inserte imagen) | (inserte imagen) |

## 🚀 Instalación

### Requisitos previos
- Flutter SDK instalado
- Backend corriendo en `http://localhost:8000`

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/Tonystylex17-09/americafitness-mobile.git
cd americafitness-mobile

# Obtener dependencias
flutter pub get

# Ejecutar en web
flutter run -d chrome

# O en dispositivo Android/iOS
flutter run

