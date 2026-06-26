from slugify import slugify


def generate_site(description, site_type, goal, style):

    title = description.split(".")[0][:60]

    return {

        "siteName": title,

        "siteType": site_type,

        "goal": goal,

        "style": style,

        "pages": [

            {

                "title": "Главная",

                "slug": "/",

                "type": "home",

                "sections": [

                    {

                        "type": "hero",

                        "title": title,

                        "subtitle": description,

                        "buttonText": "Оставить заявку"

                    },

                    {

                        "type": "features",

                        "title": "Почему выбирают нас",

                        "items": [

                            "Высокое качество",

                            "Современный дизайн",

                            "Быстрая работа",

                            "Поддержка клиентов"

                        ]

                    },

                    {

                        "type": "text",

                        "title": "О проекте",

                        "description": description

                    },

                    {

                        "type": "contact",

                        "title": "Контакты",

                        "phone": "+7 (900) 000-00-00",

                        "email": "info@example.ru",

                        "address": "Ваш адрес"

                    }

                ]

            }

        ]

    }
