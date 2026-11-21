"""Вымышленные демонстрационные данные: пользователи, расписание, изменения, зачётные книжки, заявки, объявления.

Все ФИО, номера зачёток, адреса e-mail, оценки и обращения придуманы для прототипа.
Даты привязаны к осеннему семестру 2026/27 (период конкурса — конец ноября 2026).
"""
from __future__ import annotations

P = {1: ("08:30", "10:05"), 2: ("10:15", "11:50"), 3: ("12:00", "13:35"), 4: ("13:50", "15:25"),
     5: ("15:40", "17:15"), 6: ("17:25", "19:00")}

STUDENTS = [
    {
        "login": "student1", "password_setting": "demo_password_student1",
        "profile": {
            "last_name": "Воронцова", "first_name": "Анна", "middle_name": "Сергеевна",
            "faculty_code": "ИУ", "faculty_name": "Информатика и системы управления",
            "program_code": "09.03.01", "program_name": "Информатика и вычислительная техника",
            "profile_name": "Системы обработки информации и управления",
            "education_level": "Бакалавриат", "study_form": "Очная", "funding": "Бюджет",
            "course": 2, "group_name": "ИУ5-34Б", "record_book_number": "25И0417",
            "email": "anna.vorontsova@student.example", "enrollment_year": 2025,
            "curator": "Мельникова Дарья Игоревна",
        },
    },
    {
        "login": "student2", "password_setting": "demo_password_student2",
        "profile": {
            "last_name": "Калинин", "first_name": "Максим", "middle_name": "Андреевич",
            "faculty_code": "РК", "faculty_name": "Робототехника и комплексная автоматизация",
            "program_code": "15.03.06", "program_name": "Мехатроника и робототехника",
            "profile_name": "Автономные робототехнические системы",
            "education_level": "Бакалавриат", "study_form": "Очная", "funding": "Бюджет",
            "course": 3, "group_name": "РК9-51Б", "record_book_number": "24Р1182",
            "email": "maksim.kalinin@student.example", "enrollment_year": 2024,
            "curator": "Орлов Кирилл Дмитриевич",
        },
    },
]

STAFF = {
    "login": "dekanat", "password_setting": "demo_password_staff",
    "profile": {"last_name": "Котова", "first_name": "Елена", "middle_name": "Павловна",
                "position": "Специалист по учебно-методической работе",
                "department": "Деканат (вымышленный)", "email": "e.kotova@uni.example"},
}

# (день недели 0=пн, пара, дисциплина, тип, преподаватель, аудитория, чётность)
SCHEDULE = {
    "ИУ5-34Б": [
        (0, 1, "calculus3", "lecture", "belov", "ГУК 501", "all"),
        (0, 2, "diffeq", "lecture", "sokolova", "ГУК 501", "all"),
        (0, 3, "english-2", "seminar", "kravets", "УЛК 318", "all"),
        (1, 2, "oop-cpp", "lecture", "melnikova", "ГУК 395", "all"),
        (1, 3, "oop-cpp", "lab", "nikitina", "УЛК 723", "odd"),
        (1, 3, "discrete-math", "seminar", "zaitsev", "ГУК 412", "even"),
        (1, 4, "physics-em", "lecture", "grigoriev", "ГУК 527", "all"),
        (2, 1, "physics-em", "lab", "grigoriev", "Лаб. корпус 210", "even"),
        (2, 2, "calculus3", "seminar", "ershov", "ГУК 418", "all"),
        (2, 3, "diffeq", "seminar", "sokolova", "ГУК 418", "all"),
        (3, 3, "discrete-math", "lecture", "zaitsev", "ГУК 501", "all"),
        (3, 4, "eng-graphics", "seminar", "fomin", "ГУК 830", "all"),
        (3, 5, "oop-cpp", "seminar", "nikitina", "УЛК 723", "odd"),
        (4, 1, "physics-em", "seminar", "grigoriev", "ГУК 334", "all"),
        (4, 2, "calculus3", "seminar", "ershov", "ГУК 418", "odd"),
        (4, 2, "diffeq", "seminar", "sokolova", "ГУК 420", "even"),
        (4, 3, "english-2", "seminar", "kravets", "УЛК 318", "all"),
        (5, 2, "discrete-math", "seminar", "zaitsev", "ГУК 412", "odd"),
        (5, 2, "eng-graphics", "lecture", "fomin", "ГУК 830", "even"),
    ],
    "РК9-51Б": [
        (0, 2, "control-theory", "lecture", "tarasov", "УЛК 402", "all"),
        (0, 3, "control-theory", "seminar", "tarasov", "УЛК 410", "odd"),
        (0, 3, "control-theory", "lab", "demidov", "Лаб. 115", "even"),
        (0, 4, "economics", "lecture", "savelieva", "ГУК 501", "all"),
        (1, 1, "probability", "lecture", "lebedeva", "ГУК 330", "all"),
        (1, 2, "probability", "seminar", "lebedeva", "ГУК 332", "all"),
        (1, 3, "mcu", "lab", "demidov", "Лаб. 117", "all"),
        (2, 2, "tmm", "lecture", "yakovlev", "ГУК 640", "all"),
        (2, 3, "tmm", "seminar", "yakovlev", "ГУК 642", "all"),
        (2, 4, "english-3", "seminar", "romanova", "УЛК 320", "all"),
        (3, 1, "electronics", "lecture", "polyakova", "ГУК 527", "all"),
        (3, 2, "electronics", "lab", "polyakova", "Лаб. 305", "odd"),
        (3, 3, "mcu", "lecture", "orlov", "УЛК 402", "all"),
        (4, 2, "economics", "seminar", "savelieva", "ГУК 214", "all"),
        (4, 3, "probability", "seminar", "lebedeva", "ГУК 332", "even"),
        (4, 4, "tmm", "seminar", "yakovlev", "ГУК 642", "odd"),
        (5, 1, "english-3", "seminar", "romanova", "УЛК 320", "odd"),
    ],
}

# Изменения расписания: (дата, группа, тип, (дисциплина, тип занятия) исходного занятия или None, параметры)
SCHEDULE_CHANGES = [
    ("2026-11-23", "ИУ5-34Б", "room", ("calculus3", "lecture"), {"new_room": "ГУК 214", "reason": "в аудитории ГУК 501 ремонт проектора"}),
    ("2026-11-24", "ИУ5-34Б", "cancelled", ("oop-cpp", "lab"), {"reason": "преподаватель в командировке, защита ЛР-5 — на следующем занятии"}),
    ("2026-11-25", "ИУ5-34Б", "moved", ("calculus3", "seminar"), {"new_date": "2026-11-27", "pair": 5, "new_room": "ГУК 418",
                                                                   "reason": "аудитория занята под олимпиаду"}),
    ("2026-11-26", "ИУ5-34Б", "teacher", ("eng-graphics", "seminar"), {"teacher": "lavrova"}),
    ("2026-11-27", "ИУ5-34Б", "added", None, {"discipline": "discrete-math", "lesson_type": "consultation", "pair": 4,
                                              "new_room": "ГУК 412", "teacher": "zaitsev", "reason": "консультация перед рубежным контролем 2"}),
    ("2026-12-01", "ИУ5-34Б", "cancelled", ("discrete-math", "seminar"), {"reason": "заседание учёного совета"}),
    ("2026-12-02", "ИУ5-34Б", "room", ("physics-em", "lab"), {"new_room": "Лаб. корпус 214"}),
    ("2026-11-23", "РК9-51Б", "cancelled", ("control-theory", "seminar"), {"reason": "преподаватель на научной конференции"}),
    ("2026-11-24", "РК9-51Б", "room", ("probability", "lecture"), {"new_room": "ГУК 214"}),
    ("2026-11-25", "РК9-51Б", "moved", ("tmm", "seminar"), {"new_date": "2026-11-28", "pair": 2, "new_room": "ГУК 642",
                                                             "reason": "перенос по решению кафедры"}),
    ("2026-11-26", "РК9-51Б", "teacher", ("mcu", "lecture"), {"teacher": "demidov"}),
    ("2026-11-27", "РК9-51Б", "added", None, {"discipline": "tmm", "lesson_type": "consultation", "pair": 5, "new_room": "ГУК 642",
                                              "teacher": "yakovlev", "reason": "консультация для студентов с задолженностями по модулям 1–2"}),
    ("2026-12-02", "РК9-51Б", "cancelled", ("english-3", "seminar"), {"reason": "методический день кафедры"}),
    ("2026-12-03", "РК9-51Б", "room", ("electronics", "lecture"), {"new_room": "ГУК 501"}),
]

# Зачётная книжка: (семестр, дисциплина, тип, баллы, grade_key, ЗЕ, дата)
RECORD_BOOK = {
    "student1": [
        (1, "Математический анализ (часть 1)", "exam", 88, "excellent", 6, "2026-01-16"),
        (1, "Аналитическая геометрия", "exam", 79, "good", 4, "2026-01-21"),
        (1, "Основы программирования", "distributed_exam", 92, "excellent", 5, "2025-12-24"),
        (1, "Информатика", "credit", 75, "passed", 3, "2025-12-22"),
        (1, "История России", "credit", 81, "passed", 2, "2025-12-19"),
        (1, "Иностранный язык", "credit", 84, "passed", 2, "2025-12-20"),
        (2, "Математический анализ (часть 2)", "exam", 74, "good", 6, "2026-06-15"),
        (2, "Линейная алгебра", "exam", 86, "excellent", 4, "2026-06-20"),
        (2, "Физика: механика", "exam", 77, "good", 5, "2026-06-25"),
        (2, "Алгоритмические языки", "distributed_exam", 90, "excellent", 5, "2026-05-30"),
        (2, "Иностранный язык", "credit", 80, "passed", 2, "2026-05-28"),
        (2, "Инженерная графика (часть 1)", "credit", 78, "passed", 3, "2026-05-27"),
    ],
    "student2": [
        (1, "Математический анализ (часть 1)", "exam", 64, "satisfactory", 6, "2025-01-17"),
        (1, "Аналитическая геометрия", "exam", 72, "good", 4, "2025-01-22"),
        (1, "Информатика", "credit", 70, "passed", 3, "2024-12-23"),
        (1, "Инженерная графика", "credit", 66, "passed", 3, "2024-12-25"),
        (1, "История России", "credit", 75, "passed", 2, "2024-12-20"),
        (2, "Математический анализ (часть 2)", "exam", 61, "satisfactory", 6, "2025-06-16"),
        (2, "Физика: механика", "exam", 68, "satisfactory", 5, "2025-06-21"),
        (2, "Программирование", "distributed_exam", 78, "good", 4, "2025-05-30"),
        (2, "Иностранный язык", "credit", 71, "passed", 2, "2025-05-27"),
        (3, "Дифференциальные уравнения", "exam", 63, "satisfactory", 4, "2026-01-15"),
        (3, "Теоретическая механика", "exam", 70, "satisfactory", 5, "2026-01-20"),
        (3, "Сопротивление материалов", "exam", 66, "satisfactory", 5, "2026-01-26"),
        (3, "Основы робототехники", "distributed_exam", 81, "good", 4, "2025-12-26"),
        (4, "Теоретическая механика (часть 2)", "exam", 73, "good", 5, "2026-06-17"),
        (4, "Детали машин", "distributed_exam", 69, "satisfactory", 4, "2026-05-29"),
        (4, "Метрология и стандартизация", "credit", 76, "passed", 2, "2026-05-26"),
        (4, "Иностранный язык", "credit", 68, "passed", 2, "2026-05-25"),
    ],
}

# Заявки: статусы проходят через историю; (статус, время, роль, комментарий)
APPLICATIONS = {
    "student1": [
        {"type": "study_certificate",
         "payload": {"destination": "По месту работы родителей", "copies": 2, "delivery": "paper"},
         "history": [("draft", "2026-11-16T09:10", "student", None), ("submitted", "2026-11-16T09:12", "student", None),
                     ("in_progress", "2026-11-16T14:30", "staff", None),
                     ("ready", "2026-11-18T11:05", "staff", "Справка готова. Два экземпляра ждут вас в деканате, каб. 245.")]},
        {"type": "scholarship_certificate",
         "payload": {"period_from": "2026-09-01", "period_to": "2026-11-30", "delivery": "electronic"},
         "history": [("draft", "2026-11-19T10:00", "student", None), ("submitted", "2026-11-19T10:01", "student", None),
                     ("in_progress", "2026-11-20T12:15", "staff", None)]},
        {"type": "dean_question",
         "payload": {"topic": "study", "subject": "Перезачёт онлайн-курса из летней школы",
                     "message": "Летом я прошла онлайн-курс по алгоритмам и структурам данных (72 часа) и получила сертификат. Можно ли перезачесть его как факультатив?"},
         "history": [("draft", "2026-11-05T18:20", "student", None), ("submitted", "2026-11-05T18:21", "student", None),
                     ("in_progress", "2026-11-06T10:40", "staff", None),
                     ("completed", "2026-11-10T15:00", "staff",
                      "Да, перезачёт возможен как факультативная дисциплина. Принесите оригинал сертификата в деканат до 1 декабря — оформим заявление на месте.")]},
        {"type": "transcript",
         "payload": {"scope": "all", "language": "en", "delivery": "electronic"},
         "history": [("draft", "2026-10-20T11:00", "student", None), ("submitted", "2026-10-20T11:02", "student", None),
                     ("in_progress", "2026-10-21T09:30", "staff", None),
                     ("ready", "2026-10-24T13:00", "staff", "Электронная выписка сформирована и доступна в карточке заявки.")]},
        {"type": "individual_schedule", "payload": {"reason": "competition"},
         "history": [("draft", "2026-11-21T20:15", "student", None)]},
    ],
    "student2": [
        {"type": "military_certificate",
         "payload": {"military_office": "Военный комиссариат Лефортовского района (вымышленный)", "delivery": "paper"},
         "history": [("draft", "2026-11-20T16:38", "student", None), ("submitted", "2026-11-20T16:40", "student", None)]},
        {"type": "individual_schedule",
         "payload": {"discipline_key": "tmm", "reason": "illness",
                     "details": "В октябре две недели был на больничном и пропустил часть занятий по ТММ. Прошу разрешить пересдать работы модулей 1–2 в декабре."},
         "history": [("draft", "2026-11-17T21:00", "student", None), ("submitted", "2026-11-17T21:02", "student", None),
                     ("in_progress", "2026-11-18T10:20", "staff", None),
                     ("needs_info", "2026-11-19T12:45", "staff",
                      "Уточните, пожалуйста, номер и даты медицинской справки и какие именно работы нужно пересдать (ДЗ-1, РК-1, ДЗ-2 или РК-2).")]},
        {"type": "study_certificate",
         "payload": {"destination": "Для оформления социальной транспортной карты", "copies": 1, "delivery": "paper"},
         "history": [("draft", "2026-10-01T08:50", "student", None), ("submitted", "2026-10-01T08:52", "student", None),
                     ("in_progress", "2026-10-01T13:10", "staff", None),
                     ("ready", "2026-10-03T10:00", "staff", "Справка готова, каб. 245."),
                     ("completed", "2026-10-06T14:30", "staff", "Справка выдана лично.")]},
        {"type": "material_support",
         "payload": {"reason": "difficult_situation", "details": "Прошу оказать материальную помощь в связи с непредвиденными расходами на ремонт ноутбука, необходимого для учёбы."},
         "history": [("draft", "2026-10-15T19:00", "student", None), ("submitted", "2026-10-15T19:05", "student", None),
                     ("in_progress", "2026-10-16T11:00", "staff", None),
                     ("rejected", "2026-10-22T16:20", "staff",
                      "По этому основанию материальная помощь назначается после собеседования в студенческом совете. Запишитесь на собеседование и подайте заявление повторно.")]},
    ],
}

ANNOUNCEMENTS = [
    ("2026-11-12T09:00", "Зимняя экзаменационная сессия: график опубликован",
     "Сессия пройдёт с 9 по 31 января 2027 года. Даты и аудитории экзаменов — в разделе «Учёба», вкладка «Сессия».", "normal", "/study?tab=session"),
    ("2026-11-18T10:00", "Приём документов на повышенную стипендию — до 5 декабря",
     "Студенты с достижениями в учёбе, научной, общественной, спортивной или культурной деятельности могут подать документы "
     "на повышенную стипендию. Подробности — в деканате (информация вымышлена).", "high", None),
    ("2026-11-20T15:00", "Изменение часов приёма деканата 23–29 ноября",
     "В связи с заседанием учёного совета на этой неделе деканат принимает студентов с 11:00 до 16:00. "
     "Справки по-прежнему можно заказать онлайн в разделе «Заявки».", "normal", "/applications/new"),
]

# Недавние уведомления о баллах: (логин, дисциплина, ключ работы, время)
GRADE_NOTICES = [
    ("student1", "calculus3", "rk2", "2026-11-13T17:00"),
    ("student1", "oop-cpp", "rk1", "2026-11-15T12:30"),
    ("student1", "discrete-math", "dz2", "2026-11-09T19:10"),
    ("student2", "tmm", "rk2", "2026-11-15T18:00"),
    ("student2", "mcu", "rk1", "2026-11-14T16:45"),
    ("student2", "control-theory", "rk2", "2026-11-14T11:20"),
]
