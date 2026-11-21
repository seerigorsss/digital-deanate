"""ORM-модели. Описание сущностей и связей — docs/data-model.md."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


TS = DateTime(timezone=True)


# ---------------------------------------------------------------- пользователи и сессии
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))  # student | staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)

    student_profile: Mapped[StudentProfile | None] = relationship(back_populates="user", uselist=False)
    staff_profile: Mapped[StaffProfile | None] = relationship(back_populates="user", uselist=False)


class AuthSession(Base):
    """Серверная сессия. В БД хранится только SHA-256 от токена из cookie."""

    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(token) hex
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TS)
    last_seen_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    last_name: Mapped[str] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(64))
    middle_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    faculty_code: Mapped[str] = mapped_column(String(16))
    faculty_name: Mapped[str] = mapped_column(String(200))
    program_code: Mapped[str] = mapped_column(String(16))
    program_name: Mapped[str] = mapped_column(String(200))
    profile_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    education_level: Mapped[str] = mapped_column(String(64))
    study_form: Mapped[str] = mapped_column(String(32))
    funding: Mapped[str] = mapped_column(String(32))
    course: Mapped[int] = mapped_column(Integer)
    group_name: Mapped[str] = mapped_column(String(32), index=True)
    record_book_number: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(128))
    enrollment_year: Mapped[int] = mapped_column(Integer)
    curator: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user: Mapped[User] = relationship(back_populates="student_profile")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)


class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    last_name: Mapped[str] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(64))
    middle_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    position: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(128))

    user: Mapped[User] = relationship(back_populates="staff_profile")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)


# ---------------------------------------------------------------- учебный план
class AcademicPeriod(Base):
    __tablename__ = "academic_periods"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(128))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    session_starts_on: Mapped[date] = mapped_column(Date)
    session_ends_on: Mapped[date] = mapped_column(Date)
    week1_monday: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    full_name: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(128))
    department: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(128))


class Discipline(Base):
    __tablename__ = "disciplines"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"))
    title: Mapped[str] = mapped_column(String(200))
    short_title: Mapped[str] = mapped_column(String(64))
    department: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    lecturer_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)

    lecturer: Mapped[Teacher | None] = relationship()
    assessment: Mapped[AssessmentConfiguration] = relationship(back_populates="discipline", uselist=False)
    modules: Mapped[list[Module]] = relationship(back_populates="discipline", order_by="Module.ordinal")
    topics: Mapped[list[Topic]] = relationship(back_populates="discipline", order_by="Topic.ordinal")


class AssessmentConfiguration(Base):
    """Схема аттестации дисциплины: тип A/B/C и параметры (ТЗ §14.2)."""

    __tablename__ = "assessment_configurations"
    id: Mapped[int] = mapped_column(primary_key=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"), unique=True)
    assessment_type: Mapped[str] = mapped_column(String(32))  # credit | distributed_exam | exam
    semester_points_max: Mapped[float] = mapped_column(Float)
    passing_threshold: Mapped[float] = mapped_column(Float, default=60)
    exam_points_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    exam_points_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exam_room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    grade_bands: Mapped[list | None] = mapped_column(JSON, nullable=True)  # переопределение шкалы

    discipline: Mapped[Discipline] = relationship(back_populates="assessment")


class Module(Base):
    __tablename__ = "modules"
    id: Mapped[int] = mapped_column(primary_key=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16))  # completed | in_progress | upcoming

    discipline: Mapped[Discipline] = relationship(back_populates="modules")
    items: Mapped[list[AssessmentItem]] = relationship(back_populates="module", order_by="AssessmentItem.id")


class AssessmentItem(Base):
    """Вид работы внутри модуля (ДЗ, ЛР, РК, тест, проект) с максимальным баллом."""

    __tablename__ = "assessment_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(32))
    max_points: Mapped[float] = mapped_column(Float)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    module: Mapped[Module] = relationship(back_populates="items")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "discipline_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"))
    period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"))

    discipline: Mapped[Discipline] = relationship()
    results: Mapped[list[ItemResult]] = relationship(back_populates="enrollment")
    exam_result: Mapped[ExamResult | None] = relationship(back_populates="enrollment", uselist=False)


class ItemResult(Base):
    """Фактический балл студента за вид работы (ModuleResult в терминах ТЗ)."""

    __tablename__ = "item_results"
    __table_args__ = (UniqueConstraint("enrollment_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("assessment_items.id", ondelete="CASCADE"))
    points: Mapped[float] = mapped_column(Float)
    graded_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    graded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    enrollment: Mapped[Enrollment] = relationship(back_populates="results")
    item: Mapped[AssessmentItem] = relationship()


class ExamResult(Base):
    __tablename__ = "exam_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), unique=True)
    points: Mapped[float] = mapped_column(Float)
    taken_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    enrollment: Mapped[Enrollment] = relationship(back_populates="exam_result")


class RecordBookEntry(Base):
    """Итоговая оценка прошлого семестра (зачётная книжка)."""

    __tablename__ = "record_book_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    semester: Mapped[int] = mapped_column(Integer)
    discipline_title: Mapped[str] = mapped_column(String(200))
    assessment_type: Mapped[str] = mapped_column(String(32))
    points: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade_key: Mapped[str] = mapped_column(String(32))  # excellent | good | satisfactory | passed
    grade_label: Mapped[str] = mapped_column(String(64))
    credits: Mapped[int] = mapped_column(Integer, default=0)
    passed_on: Mapped[date | None] = mapped_column(Date, nullable=True)


# ---------------------------------------------------------------- расписание
class LessonTemplate(Base):
    """Регулярное занятие группы в недельной сетке (числитель/знаменатель)."""

    __tablename__ = "lesson_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    period_id: Mapped[int] = mapped_column(ForeignKey("academic_periods.id"))
    group_name: Mapped[str] = mapped_column(String(32), index=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = понедельник … 5 = суббота
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    lesson_type: Mapped[str] = mapped_column(String(16))  # lecture | seminar | lab | consultation
    room: Mapped[str] = mapped_column(String(64))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    week_parity: Mapped[str] = mapped_column(String(8), default="all")  # all | odd | even

    discipline: Mapped[Discipline] = relationship()
    teacher: Mapped[Teacher | None] = relationship()


class ScheduleChange(Base):
    """Изменение расписания на конкретную дату: отмена, перенос, замена, доп. занятие."""

    __tablename__ = "schedule_changes"
    id: Mapped[int] = mapped_column(primary_key=True)
    group_name: Mapped[str] = mapped_column(String(32), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    change_type: Mapped[str] = mapped_column(String(16))  # cancelled | moved | room | teacher | added
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lesson_templates.id", ondelete="CASCADE"), nullable=True)
    new_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    new_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    new_room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    discipline_id: Mapped[int | None] = mapped_column(ForeignKey("disciplines.id"), nullable=True)
    lesson_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    lesson: Mapped[LessonTemplate | None] = relationship()
    new_teacher: Mapped[Teacher | None] = relationship(foreign_keys=[new_teacher_id])
    discipline: Mapped[Discipline | None] = relationship()


# ---------------------------------------------------------------- темы и материалы
class Topic(Base):
    __tablename__ = "topics"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    discipline_id: Mapped[int] = mapped_column(ForeignKey("disciplines.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[int | None] = mapped_column(ForeignKey("modules.id", ondelete="SET NULL"), nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300))

    discipline: Mapped[Discipline] = relationship(back_populates="topics")
    module: Mapped[Module | None] = relationship()
    links: Mapped[list[TopicResource]] = relationship(back_populates="topic")


class LearningResource(Base):
    __tablename__ = "learning_resources"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    resource_type: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(200))
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    url: Mapped[str] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(8))
    summary: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String(16), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    link_status: Mapped[str] = mapped_column(String(16))  # verified | unverified | broken
    checked_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    access_note: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TopicResource(Base):
    __tablename__ = "topic_resources"
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("learning_resources.id", ondelete="CASCADE"), primary_key=True)
    relevance: Mapped[str] = mapped_column(Text, default="")

    topic: Mapped[Topic] = relationship(back_populates="links")
    resource: Mapped[LearningResource] = relationship()


# ---------------------------------------------------------------- заявки
class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TS, default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)

    history: Mapped[list[ApplicationStatusHistory]] = relationship(
        back_populates="application", order_by="ApplicationStatusHistory.id", cascade="all, delete-orphan"
    )
    messages: Mapped[list[ApplicationMessage]] = relationship(
        back_populates="application", order_by="ApplicationMessage.id", cascade="all, delete-orphan"
    )
    user: Mapped[User] = relationship()


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role: Mapped[str] = mapped_column(String(16))  # student | staff | system
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="history")


class ApplicationMessage(Base):
    __tablename__ = "application_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_role: Mapped[str] = mapped_column(String(16))
    author_name: Mapped[str] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow)

    application: Mapped[Application] = relationship(back_populates="messages")


# ---------------------------------------------------------------- уведомления
class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[str] = mapped_column(String(64), default="all")  # all | faculty:<код> | group:<группа>
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(TS, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "source_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))  # announcement | deadline | schedule | application | grade
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(300), nullable=True)
    importance: Mapped[str] = mapped_column(String(16), default="normal")  # normal | high
    source_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TS, default=utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(TS, nullable=True)
