from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    USER = "user"
    GYM_ADMIN = "gym_admin"
    SUPER_ADMIN = "super_admin"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Streak
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_check_in_date = Column(DateTime, nullable=True)
    
    gym_admin_for = relationship("Gym", back_populates="admin", foreign_keys="Gym.admin_id")
    reservations = relationship("Reservation", back_populates="user")
    routines = relationship("Routine", back_populates="user")
    check_ins = relationship("CheckIn", back_populates="user", foreign_keys="CheckIn.user_id")
    purchases = relationship("Purchase", back_populates="user")
    points = relationship("UserPoints", back_populates="user", uselist=False)
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")
    exercises = relationship("Exercise", back_populates="user")
    challenges = relationship("UserChallenge", back_populates="user")
    meal_plans = relationship("MealPlan", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")

class Gym(Base):
    __tablename__ = "gyms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    admin_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("User", back_populates="gym_admin_for", foreign_keys=[admin_id])
    classes = relationship("Class", back_populates="gym")
    check_ins = relationship("CheckIn", back_populates="gym", foreign_keys="CheckIn.gym_id")

class Class(Base):
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    instructor = Column(String(100), nullable=True)
    capacity = Column(Integer, default=20)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    gym_id = Column(Integer, ForeignKey("gyms.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    gym = relationship("Gym", back_populates="classes")
    reservations = relationship("Reservation", back_populates="class_item")

class Reservation(Base):
    __tablename__ = "reservations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    class_id = Column(Integer, ForeignKey("classes.id"))
    status = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reservations")
    class_item = relationship("Class", back_populates="reservations")

class Routine(Base):
    __tablename__ = "routines"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    exercises = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="routines")

class CheckIn(Base):
    __tablename__ = "check_ins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=True)
    check_in_time = Column(DateTime, default=datetime.utcnow)
    check_out_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="check_ins", foreign_keys=[user_id])
    gym = relationship("Gym", back_populates="check_ins", foreign_keys=[gym_id])

class Purchase(Base):
    __tablename__ = "purchases"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    points_earned = Column(Integer, nullable=False)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="purchases")

class UserPoints(Base):
    __tablename__ = "user_points"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    total_points = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="points")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    points_price = Column(Integer, nullable=True)
    image_url = Column(String(200), nullable=True)
    stock = Column(Integer, default=0)
    category = Column(String(50), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class Exercise(Base):
    __tablename__ = "exercises"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="exercises")
    records = relationship("ExerciseRecord", back_populates="exercise")

class ExerciseRecord(Base):
    __tablename__ = "exercise_records"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    day_number = Column(Integer, nullable=False)
    sets = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    exercise = relationship("Exercise", back_populates="records")

class Challenge(Base):
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String(50), nullable=False)  # checkins, workouts, points
    goal_value = Column(Integer, nullable=False)
    reward_points = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserChallenge(Base):
    __tablename__ = "user_challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    challenge_id = Column(Integer, ForeignKey("challenges.id"))
    progress = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="challenges")
    challenge = relationship("Challenge")

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    condition_type = Column(String(50), nullable=False)  # streak, checkins, points, workouts
    condition_value = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_id = Column(Integer, ForeignKey("badges.id"))
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")

class MealPlan(Base):
    __tablename__ = "meal_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal = Column(String(50), nullable=False)  # muscle_gain, fat_loss, maintenance
    calories_target = Column(Integer, nullable=False)
    protein_grams = Column(Integer, nullable=False)
    carbs_grams = Column(Integer, nullable=False)
    fat_grams = Column(Integer, nullable=False)
    meals_data = Column(Text, nullable=True)  # JSON con comidas
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="meal_plans")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    status = Column(String(20), default="inactive")  # active, inactive, cancelled
    plan = Column(String(20), default="free")  # free, premium
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="subscription")

# Agregar relaciones en User
User.subscription = relationship("Subscription", back_populates="user", uselist=False)
User.challenges = relationship("UserChallenge", back_populates="user")
User.meal_plans = relationship("MealPlan", back_populates="user")
User.badges = relationship("UserBadge", back_populates="user")