from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
import database
import models
import auth

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="AméricaFitness API",
    description="API para gestión de gimnasios con tienda y puntos",
    version="2.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AméricaFitness API", "status": "online", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ========== USUARIOS ==========
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "user"

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuario o email ya registrado")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "username": db_user.username, "email": db_user.email, "role": db_user.role}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "role": user.role}

@app.get("/users/me")
def get_me(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    badges = db.query(models.UserBadge).filter(
        models.UserBadge.user_id == current_user.id
    ).all()
    
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "badges": [{"id": b.badge_id, "earned_at": b.earned_at} for b in badges]
    }

# ========== GIMNASIOS ==========
class GymCreate(BaseModel):
    name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None

@app.post("/gyms")
def create_gym(
    gym: GymCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role not in ["gym_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    db_gym = models.Gym(
        name=gym.name,
        address=gym.address,
        latitude=gym.latitude,
        longitude=gym.longitude,
        phone=gym.phone,
        email=gym.email,
        admin_id=current_user.id
    )
    db.add(db_gym)
    db.commit()
    db.refresh(db_gym)
    return db_gym

@app.get("/gyms")
def get_gyms(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    gyms = db.query(models.Gym).offset(skip).limit(limit).all()
    return gyms

# ========== CLASES ==========
class ClassCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instructor: Optional[str] = None
    capacity: int = 20
    start_time: datetime
    end_time: datetime
    gym_id: int

@app.post("/classes")
def create_class(
    class_data: ClassCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role not in ["gym_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    db_class = models.Class(
        name=class_data.name,
        description=class_data.description,
        instructor=class_data.instructor,
        capacity=class_data.capacity,
        start_time=class_data.start_time,
        end_time=class_data.end_time,
        gym_id=class_data.gym_id
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class

@app.get("/classes")
def get_classes(
    gym_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Class)
    if gym_id:
        query = query.filter(models.Class.gym_id == gym_id)
    classes = query.offset(skip).limit(limit).all()
    return classes

# ========== RESERVAS ==========
class ReservationCreate(BaseModel):
    class_id: int

@app.post("/reservations")
def create_reservation(
    reservation: ReservationCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    class_item = db.query(models.Class).filter(models.Class.id == reservation.class_id).first()
    if not class_item:
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    
    reserved_count = db.query(models.Reservation).filter(
        models.Reservation.class_id == reservation.class_id,
        models.Reservation.status == "confirmed"
    ).count()
    
    if reserved_count >= class_item.capacity:
        raise HTTPException(status_code=400, detail="No hay cupos disponibles")
    
    existing = db.query(models.Reservation).filter(
        models.Reservation.user_id == current_user.id,
        models.Reservation.class_id == reservation.class_id,
        models.Reservation.status == "confirmed"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya reservaste esta clase")
    
    db_reservation = models.Reservation(
        user_id=current_user.id,
        class_id=reservation.class_id
    )
    db.add(db_reservation)
    db.commit()
    db.refresh(db_reservation)
    return db_reservation

@app.get("/my-reservations")
def get_my_reservations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    reservations = db.query(models.Reservation).filter(
        models.Reservation.user_id == current_user.id
    ).all()
    return reservations

# ========== RUTINAS ==========
class RoutineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    exercises: Optional[str] = None

@app.post("/routines")
def create_routine(
    routine: RoutineCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_routine = models.Routine(
        user_id=current_user.id,
        name=routine.name,
        description=routine.description,
        exercises=routine.exercises
    )
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return db_routine

@app.get("/my-routines")
def get_my_routines(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    routines = db.query(models.Routine).filter(
        models.Routine.user_id == current_user.id
    ).all()
    return routines

# ========== CHECK-IN ==========
def update_streak(user, db):
    today = date.today()
    last_checkin = user.last_check_in_date
    
    if last_checkin is None:
        user.current_streak = 1
    elif last_checkin.date() == today - timedelta(days=1):
        user.current_streak += 1
    elif last_checkin.date() == today:
        pass
    else:
        user.current_streak = 1
    
    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak
    
    user.last_check_in_date = datetime.now()
    db.commit()
    
    check_badges(user.id, "streak", user.current_streak, db)

def check_badges(user_id, condition_type, condition_value, db):
    badges = db.query(models.Badge).filter(
        models.Badge.condition_type == condition_type,
        models.Badge.condition_value <= condition_value
    ).all()
    
    for badge in badges:
        existing = db.query(models.UserBadge).filter(
            models.UserBadge.user_id == user_id,
            models.UserBadge.badge_id == badge.id
        ).first()
        if not existing:
            new_badge = models.UserBadge(user_id=user_id, badge_id=badge.id)
            db.add(new_badge)
            db.commit()

def update_challenge_progress_for_user(user_id, goal_type, increment, db):
    challenges = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == user_id,
        models.UserChallenge.completed == False
    ).all()
    
    for user_challenge in challenges:
        challenge = db.query(models.Challenge).filter(models.Challenge.id == user_challenge.challenge_id).first()
        if challenge and challenge.goal_type == goal_type:
            user_challenge.progress += increment
            if user_challenge.progress >= challenge.goal_value:
                user_challenge.completed = True
                user_challenge.completed_at = datetime.utcnow()
                points_record = db.query(models.UserPoints).filter(models.UserPoints.user_id == user_id).first()
                if points_record:
                    points_record.total_points += challenge.reward_points
            db.commit()

@app.post("/check-in")
def check_in(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    active_check_in = db.query(models.CheckIn).filter(
        models.CheckIn.user_id == current_user.id,
        models.CheckIn.check_out_time == None
    ).first()
    
    if active_check_in:
        raise HTTPException(status_code=400, detail="Ya tienes un check-in activo")
    
    new_check_in = models.CheckIn(
        user_id=current_user.id,
        gym_id=None
    )
    db.add(new_check_in)
    db.commit()
    db.refresh(new_check_in)
    
    update_streak(current_user, db)
    
    points_record = db.query(models.UserPoints).filter(models.UserPoints.user_id == current_user.id).first()
    if not points_record:
        points_record = models.UserPoints(user_id=current_user.id, total_points=0)
        db.add(points_record)
    
    points_record.total_points += 10
    points_record.updated_at = datetime.utcnow()
    db.commit()
    
    update_challenge_progress_for_user(current_user.id, "checkins", 1, db)
    
    return {
        "message": "Check-in exitoso",
        "check_in_id": new_check_in.id,
        "check_in_time": new_check_in.check_in_time,
        "points_earned": 10,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak
    }

@app.post("/check-in-by-qr")
def check_in_by_qr(
    user_id: int,
    db: Session = Depends(database.get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    active_check_in = db.query(models.CheckIn).filter(
        models.CheckIn.user_id == user_id,
        models.CheckIn.check_out_time == None
    ).first()
    
    if active_check_in:
        raise HTTPException(status_code=400, detail="Ya tienes un check-in activo")
    
    new_check_in = models.CheckIn(
        user_id=user_id,
        gym_id=None
    )
    db.add(new_check_in)
    db.commit()
    db.refresh(new_check_in)
    
    update_streak(user, db)
    
    points_record = db.query(models.UserPoints).filter(models.UserPoints.user_id == user_id).first()
    if not points_record:
        points_record = models.UserPoints(user_id=user_id, total_points=0)
        db.add(points_record)
    
    points_record.total_points += 10
    points_record.updated_at = datetime.utcnow()
    db.commit()
    
    update_challenge_progress_for_user(user_id, "checkins", 1, db)
    
    return {
        "message": "Check-in exitoso",
        "user": user.username,
        "check_in_id": new_check_in.id,
        "check_in_time": new_check_in.check_in_time,
        "points_earned": 10,
        "current_streak": user.current_streak
    }

@app.post("/check-out")
def check_out(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    active_check_in = db.query(models.CheckIn).filter(
        models.CheckIn.user_id == current_user.id,
        models.CheckIn.check_out_time == None
    ).first()
    
    if not active_check_in:
        raise HTTPException(status_code=400, detail="No tienes un check-in activo")
    
    active_check_in.check_out_time = datetime.utcnow()
    db.commit()
    db.refresh(active_check_in)
    
    return {
        "message": "Check-out exitoso",
        "check_in_id": active_check_in.id,
        "check_in_time": active_check_in.check_in_time,
        "check_out_time": active_check_in.check_out_time
    }

@app.get("/my-attendance")
def get_my_attendance(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    check_ins = db.query(models.CheckIn).filter(
        models.CheckIn.user_id == current_user.id
    ).order_by(models.CheckIn.check_in_time.desc()).all()
    
    return [
        {
            "id": c.id,
            "gym_id": c.gym_id,
            "check_in_time": c.check_in_time,
            "check_out_time": c.check_out_time
        }
        for c in check_ins
    ]

# ========== PUNTOS ==========
@app.get("/my-points")
def get_my_points(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    points_record = db.query(models.UserPoints).filter(models.UserPoints.user_id == current_user.id).first()
    if not points_record:
        return {"total_points": 0}
    return {"total_points": points_record.total_points}

@app.get("/my-streak")
def get_my_streak(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return {
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "last_check_in_date": current_user.last_check_in_date
    }

# ========== PRODUCTOS ==========
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    points_price: Optional[int] = None
    image_url: Optional[str] = None
    stock: int = 0
    category: str = "general"

@app.post("/products")
def create_product(
    product: ProductCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role not in ["gym_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    db_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        points_price=product.points_price,
        image_url=product.image_url,
        stock=product.stock,
        category=product.category
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products")
def get_products(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category == category)
    products = query.offset(skip).limit(limit).all()
    return products

# ========== CARRITO ==========
class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

@app.post("/cart/add")
def add_to_cart(
    item: CartItemCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    if product.stock < item.quantity:
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    
    existing = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.product_id == item.product_id
    ).first()
    
    if existing:
        existing.quantity += item.quantity
    else:
        new_item = models.CartItem(
            user_id=current_user.id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.add(new_item)
    
    db.commit()
    return {"message": "Producto agregado al carrito"}

@app.get("/cart")
def get_cart(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()
    
    result = []
    for item in items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        result.append({
            "id": item.id,
            "product_id": item.product_id,
            "name": product.name,
            "price": product.price,
            "points_price": product.points_price,
            "image_url": product.image_url,
            "quantity": item.quantity,
            "subtotal": product.price * item.quantity
        })
    
    total = sum(item["subtotal"] for item in result)
    return {"items": result, "total": total}

@app.delete("/cart/remove/{item_id}")
def remove_from_cart(
    item_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    item = db.query(models.CartItem).filter(
        models.CartItem.id == item_id,
        models.CartItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    db.delete(item)
    db.commit()
    return {"message": "Producto eliminado del carrito"}

# ========== EJERCICIOS ==========
class ExerciseCreate(BaseModel):
    name: str

@app.post("/exercises")
def create_exercise(
    exercise: ExerciseCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    existing = db.query(models.Exercise).filter(
        models.Exercise.name == exercise.name,
        models.Exercise.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ejercicio ya existe")
    
    db_exercise = models.Exercise(
        name=exercise.name,
        user_id=current_user.id
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise

@app.get("/my-exercises")
def get_my_exercises(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    exercises = db.query(models.Exercise).filter(
        models.Exercise.user_id == current_user.id
    ).all()
    return exercises

class RecordCreate(BaseModel):
    exercise_id: int
    day_number: int
    sets: int
    weight: float
    notes: Optional[str] = None

@app.post("/exercise-record")
def add_exercise_record(
    record: RecordCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    exercise = db.query(models.Exercise).filter(
        models.Exercise.id == record.exercise_id,
        models.Exercise.user_id == current_user.id
    ).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    
    db_record = models.ExerciseRecord(
        exercise_id=record.exercise_id,
        day_number=record.day_number,
        sets=record.sets,
        weight=record.weight,
        notes=record.notes
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    update_challenge_progress_for_user(current_user.id, "workouts", 1, db)
    
    return db_record

@app.get("/exercise-records/{exercise_id}")
def get_exercise_records(
    exercise_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    exercise = db.query(models.Exercise).filter(
        models.Exercise.id == exercise_id,
        models.Exercise.user_id == current_user.id
    ).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    
    records = db.query(models.ExerciseRecord).filter(
        models.ExerciseRecord.exercise_id == exercise_id
    ).order_by(models.ExerciseRecord.day_number).all()
    return records

@app.delete("/exercises/{exercise_id}")
def delete_exercise(
    exercise_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    exercise = db.query(models.Exercise).filter(
        models.Exercise.id == exercise_id,
        models.Exercise.user_id == current_user.id
    ).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    
    # Eliminar también los registros asociados
    db.query(models.ExerciseRecord).filter(
        models.ExerciseRecord.exercise_id == exercise_id
    ).delete()
    
    db.delete(exercise)
    db.commit()
    return {"message": "Ejercicio eliminado"}
# ========== NUTRICIÓN ==========
class NutritionData(BaseModel):
    sex: str
    weight: float
    height: float
    age: int
    goal: str

PLANES_VOLUMEN_HOMBRE = {
    "nombre": "Volumen para Hombre",
    "descripcion": "Enfoque en proteínas y carbohidratos complejos para ganar masa muscular",
    "comidas": [
        {"nombre": "Desayuno", "opciones": ["Avena con plátano y huevos revueltos (3 huevos)", "Tostada integral con aguacate y pechuga de pavo"]},
        {"nombre": "Almuerzo", "opciones": ["Arroz integral + pechuga de pollo + brócoli", "Quinoa + lomo saltado de res + ensalada"]},
        {"nombre": "Merienda", "opciones": ["Yogur griego con frutos secos", "Batido de proteína con leche"]},
        {"nombre": "Cena", "opciones": ["Pescado a la plancha + puré de camote", "Tortilla de claras con espinacas"]},
    ],
    "tips": ["Aumenta porciones de carbohidratos en días de entrenamiento", "Hidrátate bien"]
}

PLANES_DEFINICION_HOMBRE = {
    "nombre": "Definición para Hombre",
    "descripcion": "Menos carbohidratos, más proteínas magras y verduras",
    "comidas": [
        {"nombre": "Desayuno", "opciones": ["Claras de huevo con espinacas y 1 tostada integral", "Batido de proteína con agua y frutos rojos"]},
        {"nombre": "Almuerzo", "opciones": ["Pechuga de pollo a la plancha + ensalada verde", "Pescado blanco + espárragos"]},
        {"nombre": "Merienda", "opciones": ["Gelatina sin azúcar", "Claras de huevo"]},
        {"nombre": "Cena", "opciones": ["Pollo con brócoli", "Atún con palta"]},
    ],
    "tips": ["Reduce carbohidratos después de las 6pm", "Incrementa cardio"]
}

PLANES_VOLUMEN_MUJER = {
    "nombre": "Volumen para Mujer",
    "descripcion": "Enfoque en proteínas magras y carbohidratos de bajo índice glucémico",
    "comidas": [
        {"nombre": "Desayuno", "opciones": ["Avena con frutos rojos y claras", "Pan integral con ricotta y miel"]},
        {"nombre": "Almuerzo", "opciones": ["Pechuga de pollo con quinoa y verduras", "Pescado con camote"]},
        {"nombre": "Merienda", "opciones": ["Yogur natural con frutas", "Frutos secos"]},
        {"nombre": "Cena", "opciones": ["Tortilla de claras con champiñones", "Salmon con espárragos"]},
    ],
    "tips": ["Mantén porciones moderadas", "No elimines grasas saludables"]
}

PLANES_DEFINICION_MUJER = {
    "nombre": "Definición para Mujer",
    "descripcion": "Alta proteína, baja en carbohidratos",
    "comidas": [
        {"nombre": "Desayuno", "opciones": ["Claras con espinacas", "Batido de proteína con agua"]},
        {"nombre": "Almuerzo", "opciones": ["Pollo a la plancha + ensalada", "Atún con palta"]},
        {"nombre": "Merienda", "opciones": ["Pepino con limón", "Gelatina sin azúcar"]},
        {"nombre": "Cena", "opciones": ["Merluza al horno con verduras", "Tortilla de claras con espárragos"]},
    ],
    "tips": ["Evita azúcares", "Prioriza verduras de hoja verde"]
}

@app.post("/calculate-nutrition")
def calculate_nutrition(data: NutritionData):
    height_m = data.height / 100
    imc = data.weight / (height_m * height_m)
    
    if data.sex == "male":
        tmb = 88.362 + (13.397 * data.weight) + (4.799 * data.height) - (5.677 * data.age)
    else:
        tmb = 447.593 + (9.247 * data.weight) + (3.098 * data.height) - (4.330 * data.age)
    
    if data.goal == "volume":
        calorias_base = tmb * 1.55
        calorias_objetivo = calorias_base + 300
    else:
        calorias_base = tmb * 1.55
        calorias_objetivo = calorias_base - 300
    
    calorias_min = calorias_objetivo - 200
    calorias_max = calorias_objetivo + 200
    
    if data.sex == "male":
        if data.goal == "volume":
            plan = PLANES_VOLUMEN_HOMBRE
        else:
            plan = PLANES_DEFINICION_HOMBRE
    else:
        if data.goal == "volume":
            plan = PLANES_VOLUMEN_MUJER
        else:
            plan = PLANES_DEFINICION_MUJER
    
    return {
        "imc": round(imc, 1),
        "tmb": round(tmb),
        "calorias_base": round(calorias_base),
        "calorias_objetivo": round(calorias_objetivo),
        "rango_calorias": {
            "min": round(calorias_min),
            "max": round(calorias_max),
            "mensaje": "Puedes consumir entre estas calorías, con margen para un dulce el fin de semana"
        },
        "plan": plan
    }
# ========== INSIGNIAS ==========
@app.get("/badges")
def get_badges(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    user_badges = db.query(models.UserBadge).filter(
        models.UserBadge.user_id == current_user.id
    ).all()
    
    result = []
    for ub in user_badges:
        badge = db.query(models.Badge).filter(models.Badge.id == ub.badge_id).first()
        if badge:
            result.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "earned_at": ub.earned_at
            })
    return result

@app.post("/badges/create-default")
def create_default_badges(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    default_badges = [
        {"name": "Primer Check-in", "description": "Realizaste tu primer check-in", "icon": "🏋️", "condition_type": "checkins", "condition_value": 1},
        {"name": "Check-in Diario", "description": "Completaste 7 check-ins", "icon": "📅", "condition_type": "checkins", "condition_value": 7},
        {"name": "Racha de 7 días", "description": "Mantuviste una racha de 7 días", "icon": "🔥", "condition_type": "streak", "condition_value": 7},
        {"name": "Racha de 30 días", "description": "Mantuviste una racha de 30 días", "icon": "⚡", "condition_type": "streak", "condition_value": 30},
        {"name": "Primer Entrenamiento", "description": "Registraste tu primer entrenamiento", "icon": "💪", "condition_type": "workouts", "condition_value": 1},
        {"name": "100 Puntos", "description": "Acumulaste 100 puntos", "icon": "⭐", "condition_type": "points", "condition_value": 100},
    ]
    
    for badge_data in default_badges:
        existing = db.query(models.Badge).filter(models.Badge.name == badge_data["name"]).first()
        if not existing:
            new_badge = models.Badge(
                name=badge_data["name"],
                description=badge_data["description"],
                icon=badge_data["icon"],
                condition_type=badge_data["condition_type"],
                condition_value=badge_data["condition_value"]
            )
            db.add(new_badge)
    
    db.commit()
    return {"message": "Insignias creadas"}

# ========== DESAFÍOS ==========
class ChallengeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    goal_type: str
    goal_value: int
    reward_points: int = 0
    start_date: datetime
    end_date: datetime

@app.post("/challenges")
def create_challenge(
    challenge: ChallengeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.role not in ["gym_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="No tienes permisos")
    
    db_challenge = models.Challenge(
        name=challenge.name,
        description=challenge.description,
        goal_type=challenge.goal_type,
        goal_value=challenge.goal_value,
        reward_points=challenge.reward_points,
        start_date=challenge.start_date,
        end_date=challenge.end_date,
        is_active=True
    )
    db.add(db_challenge)
    db.commit()
    db.refresh(db_challenge)
    return db_challenge

@app.get("/active-challenges")
def get_active_challenges(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    now = datetime.utcnow()
    challenges = db.query(models.Challenge).filter(
        models.Challenge.start_date <= now,
        models.Challenge.end_date >= now,
        models.Challenge.is_active == True
    ).all()
    
    result = []
    for challenge in challenges:
        user_challenge = db.query(models.UserChallenge).filter(
            models.UserChallenge.user_id == current_user.id,
            models.UserChallenge.challenge_id == challenge.id
        ).first()
        
        result.append({
            "id": challenge.id,
            "name": challenge.name,
            "description": challenge.description,
            "goal_type": challenge.goal_type,
            "goal_value": challenge.goal_value,
            "reward_points": challenge.reward_points,
            "progress": user_challenge.progress if user_challenge else 0,
            "completed": user_challenge.completed if user_challenge else False,
            "end_date": challenge.end_date
        })
    return result

@app.post("/update-challenge-progress/{challenge_id}")
def update_challenge_progress(
    challenge_id: int,
    progress_value: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    challenge = db.query(models.Challenge).filter(models.Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafío no encontrado")
    
    user_challenge = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == challenge_id
    ).first()
    
    if not user_challenge:
        user_challenge = models.UserChallenge(
            user_id=current_user.id,
            challenge_id=challenge_id,
            progress=0
        )
        db.add(user_challenge)
    
    user_challenge.progress = min(progress_value, challenge.goal_value)
    
    if user_challenge.progress >= challenge.goal_value and not user_challenge.completed:
        user_challenge.completed = True
        user_challenge.completed_at = datetime.utcnow()
        
        points_record = db.query(models.UserPoints).filter(models.UserPoints.user_id == current_user.id).first()
        if points_record:
            points_record.total_points += challenge.reward_points
        else:
            points_record = models.UserPoints(user_id=current_user.id, total_points=challenge.reward_points)
            db.add(points_record)
    
    db.commit()
    db.refresh(user_challenge)
    
    return {
        "progress": user_challenge.progress,
        "completed": user_challenge.completed,
        "points_earned": challenge.reward_points if user_challenge.completed else 0
    }

# ========== RANKING ==========
@app.get("/ranking")
def get_ranking(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    users = db.query(models.User).filter(
        models.User.is_active == True
    ).all()
    
    ranking = []
    for user in users:
        points = db.query(models.UserPoints).filter(models.UserPoints.user_id == user.id).first()
        total_points = points.total_points if points else 0
        ranking.append({
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "points": total_points,
            "streak": user.current_streak
        })
    
    ranking.sort(key=lambda x: x["points"], reverse=True)
    
    return ranking[:50]

# ========== PLANES DE COMIDA ==========
class MealPlanCreate(BaseModel):
    goal: str
    calories_target: int
    protein_grams: int
    carbs_grams: int
    fat_grams: int
    meals_data: Optional[str] = None

@app.post("/meal-plan")
def create_meal_plan(
    plan: MealPlanCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    existing = db.query(models.MealPlan).filter(models.MealPlan.user_id == current_user.id).first()
    if existing:
        db.delete(existing)
    
    meal_plan = models.MealPlan(
        user_id=current_user.id,
        goal=plan.goal,
        calories_target=plan.calories_target,
        protein_grams=plan.protein_grams,
        carbs_grams=plan.carbs_grams,
        fat_grams=plan.fat_grams,
        meals_data=plan.meals_data
    )
    db.add(meal_plan)
    db.commit()
    db.refresh(meal_plan)
    return meal_plan

@app.get("/my-meal-plan")
def get_my_meal_plan(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    meal_plan = db.query(models.MealPlan).filter(models.MealPlan.user_id == current_user.id).first()
    if not meal_plan:
        return None
    return meal_plan

# ========== MEMBRESÍAS ==========
class CreateSubscription(BaseModel):
    payment_method_id: str

@app.post("/create-subscription")
def create_subscription(
    data: CreateSubscription,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    subscription = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id).first()
    if not subscription:
        subscription = models.Subscription(user_id=current_user.id)
        db.add(subscription)
    
    subscription.status = "active"
    subscription.plan = "premium"
    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
    db.commit()
    
    return {"success": True, "plan": "premium", "expires_at": subscription.current_period_end}

@app.get("/my-subscription")
def get_my_subscription(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    subscription = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id).first()
    if not subscription:
        return {"plan": "free", "status": "inactive"}
    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "expires_at": subscription.current_period_end
    }

# ========== PAGOS ==========
class PaymentCreate(BaseModel):
    amount: int
    currency: str = "PEN"
    email: str
    description: str
    card_last4: Optional[str] = None
    card_type: Optional[str] = None

@app.post("/create-payment")
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    new_order = models.Order(
        user_id=current_user.id,
        total_amount=payment.amount / 100,
        status="paid"
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    cart_items = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id
    ).all()
    
    for item in cart_items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=product.price
        )
        db.add(order_item)
        db.delete(item)
    
    db.commit()
    
    return {
        "success": True,
        "charge_id": "simulacion_" + str(datetime.now().timestamp()),
        "message": "Pago procesado exitosamente",
        "order_id": new_order.id
    }

# ========== PEDIDOS ==========
@app.get("/my-orders")
def get_my_orders(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    orders = db.query(models.Order).filter(
        models.Order.user_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()
    
    result = []
    for order in orders:
        items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order.id
        ).all()
        result.append({
            "id": order.id,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "items": [{"product_name": item.product.name, "quantity": item.quantity, "price": item.price} for item in items]
        })
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
