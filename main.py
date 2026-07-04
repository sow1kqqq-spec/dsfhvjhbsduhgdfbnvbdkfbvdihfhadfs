import asyncio
import logging
import json
import os
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import re
from bs4 import BeautifulSoup


TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    'ru': {
        "main_header": "🌱 <b>Grow a Garden 2 Биржа</b>\n\n",
        "select_action": "📊 Выберите действие:",
        "btn_stock": "📊 Сток",
        "btn_predict": "🔮 Предикт",
        "btn_weather": "🌤 Погода",
        "btn_autostock": "⏱ Автостоки",
        "btn_channel": "📢 Подключить канал",
        "btn_support": "🆘 Поддержка",
        "btn_admin": "⚙️ Админ",
        "btn_language": "🌍 Язык / Language",
        "btn_back": "🔙 Назад",
        "btn_exit": "🚪 Выйти",
        "btn_seeds": "🌱 Семена",
        "btn_gears": "🛠️ Инструменты",
        "btn_crates": "📦 Ящики",
        "btn_write": "✍️ Написать",
        "btn_prev": "⬅️ Пред.",
        "btn_next": "След. ➡️",
        "predict_header": "🔮 <b>Предикт стоков</b>\n───────────────\n\nВыберите категорию прогнозов:",
        "predict_no_data": "   <i>Нет данных о редких предметах</i>\n\n",
        "predict_seeds_title": "СЕМЕНА",
        "predict_gears_title": "ИНСТРУМЕНТЫ",
        "predict_crates_title": "ЯЩИКИ",
        "stock_header": "📊 Актуальные стоки\n────────────────────\n\n",
        "stock_no_items": "   ❌ Нет предметов\n",
        "stock_countdown": "\n⏱️ Сток: {time} (МСК)\n⏳ До обновления: <b>{countdown}</b>",
        "timer_starting": "таймер запускается...",
        "timer_updating": "обновление стока...",
        "weather_header": "🌤 <b>Погода и Время</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Время суток:</b> {time}\n",
        "weather_effect": "🌦 <b>Эффект погоды:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Эффект погоды:</b> Ясно\n",
        "weather_start": "⏱️ Начало: {time} (МСК)\n",
        "weather_no_data": "🌦 <b>Эффект погоды:</b> Нет данных\n",
        "moon_schedule": "📅 <b>Расписание лунных событий:</b>\n",
        "moon_no_data": "🌙 <b>Лунный цикл:</b> Нет данных прогноза\n",
        "active_now": "активна сейчас",
        "in_mins": "через {m}м",
        "morning": "🌅 Утро",
        "day": "☀️ День",
        "evening": "🌅 Вечер",
        "night": "🌙 Ночь",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Для доступа подпишись на канал:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>А также на спонсоров:</b>\n",
        "sub_press_btn": "\n⬇️ После подписки нажми кнопку ниже.",
        "btn_subscribe": "📢 Подписаться на канал",
        "btn_check_sub": "✅ Проверить подписку",
        "sub_confirmed": "✅ <b>Подписка подтверждена!</b>\n\n🌱 Добро пожаловать!",
        "sub_failed": "❌ <b>Вы не подписаны на все каналы!</b>\n\n",
        "sub_failed_alert": "❌ Подписка не подтверждена!",
        "sub_error_alert": "❌ Вы не подписаны!",
        "support_header": "🆘 Поддержка\n───────────────\n\n📌 Задайте вопрос администратору.\nНапишите сообщение, мы ответим.\n\n💬 Нажмите кнопку ниже.",
        "support_write_msg": "✍️ Напишите сообщение\n\nОпишите проблему или задайте вопрос.\n<i>Для отмены /cancel</i>",
        "support_cancelled": "❌ Отменено",
        "support_sent": "✅ Отправлено!\n\nАдминистратор ответит.",
        "support_error": "❌ Ошибка!\n\nПопробуйте позже.",
        "auto_stock_desc": "⏱ <b>Личные уведомления о стоках</b>\n\nБот будет отправлять вам личные сообщения, когда выбранные вами семена или инструменты появятся в наличии!\n\nВыберите категорию для настройки:",
        "auto_stock_setup_seeds": "🌱 <b>Настройка уведомлений: Seeds</b>\n\nВыделите семена, о появлении которых хотите получать уведомления:",
        "auto_stock_setup_gears": "🛠️ <b>Настройка уведомлений: Gears</b>\n\nВыделите инструменты, о появлении которых хотите получать уведомления:",
        "status_on": "Включено",
        "status_off": "Выключено",
        "add_channel_desc": "🤖 <b>Подключи бота к своему каналу</b>\n\n🔹 1. Нажми на кнопку ниже\n🔹 2. Выбери свой канал\n🔹 3. Дай права администратора (обязательно)\n\n🔗 Бот будет отправлять уведомления о легендарных предметах в твой канал!",
        "btn_add_channel": "🤖 Добавить в канал",
        "lang_select": "🌍 <b>Выберите ваш язык / Choose your language:</b>",
        "lang_set": "✅ Язык установлен: {lang}",
        "rarity_common": "Обычный",
        "rarity_uncommon": "Необычный",
        "rarity_rare": "Редкий",
        "rarity_epic": "Эпический",
        "rarity_legendary": "Легендарный",
        "rarity_mythic": "Мифический",
        "rarity_super": "Супер",
        "rarity_secret": "Секретный",
        "months": {1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'},
    },
    'en': {
        "main_header": "🌱 <b>Grow a Garden 2 Stock Exchange</b>\n\n",
        "select_action": "📊 Select an action:",
        "btn_stock": "📊 Stock",
        "btn_predict": "🔮 Predict",
        "btn_weather": "🌤 Weather",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Connect Channel",
        "btn_support": "🆘 Support",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Язык / Language",
        "btn_back": "🔙 Back",
        "btn_exit": "🚪 Exit",
        "btn_seeds": "🌱 Seeds",
        "btn_gears": "🛠️ Gears",
        "btn_crates": "📦 Crates",
        "btn_write": "✍️ Write",
        "btn_prev": "⬅️ Prev",
        "btn_next": "Next ➡️",
        "predict_header": "🔮 <b>Stock Predictor</b>\n───────────────\n\nSelect a category:",
        "predict_no_data": "   <i>No data for rare items</i>\n\n",
        "predict_seeds_title": "SEEDS",
        "predict_gears_title": "GEARS",
        "predict_crates_title": "CRATES",
        "stock_header": "📊 Current Stock\n────────────────────\n\n",
        "stock_no_items": "   ❌ No items\n",
        "stock_countdown": "\n⏱️ Stock: {time} (MSK)\n⏳ Time left: <b>{countdown}</b>",
        "timer_starting": "timer starting...",
        "timer_updating": "updating stock...",
        "weather_header": "🌤 <b>Weather & Time</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Time of day:</b> {time}\n",
        "weather_effect": "🌦 <b>Weather effect:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Weather effect:</b> Clear\n",
        "weather_start": "⏱️ Started at: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Weather effect:</b> No data\n",
        "moon_schedule": "📅 <b>Moon Schedule:</b>\n",
        "moon_no_data": "🌙 <b>Moon Cycle:</b> No forecast data\n",
        "active_now": "active now",
        "in_mins": "in {m}m",
        "morning": "🌅 Morning",
        "day": "☀️ Day",
        "evening": "🌅 Evening",
        "night": "🌙 Night",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Please subscribe to our channel for access:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>And to our sponsors:</b>\n",
        "sub_press_btn": "\n⬇️ Press the button below after subscribing.",
        "btn_subscribe": "📢 Subscribe to Channel",
        "btn_check_sub": "✅ Check Subscription",
        "sub_confirmed": "✅ <b>Subscription confirmed!</b>\n\n🌱 Welcome!",
        "sub_failed": "❌ <b>You haven't subscribed to all channels!</b>\n\n",
        "sub_failed_alert": "❌ Subscription not confirmed!",
        "sub_error_alert": "❌ You are not subscribed!",
        "support_header": "🆘 Support\n───────────────\n\n📌 Ask an administrator a question.\nWrite your message and we will reply.\n\n💬 Press the button below.",
        "support_write_msg": "✍️ Write your message\n\nDescribe your issue or ask a question.\n<i>Send /cancel to cancel</i>",
        "support_cancelled": "❌ Cancelled",
        "support_sent": "✅ Sent!\n\nAn administrator will reply soon.",
        "support_error": "❌ Error!\n\nPlease try again later.",
        "auto_stock_desc": "⏱ <b>Personal Stock Notifications</b>\n\nThe bot will send you private messages when your selected seeds or gears are in stock!\n\nSelect a category to setup:",
        "auto_stock_setup_seeds": "🌱 <b>Notification Setup: Seeds</b>\n\nSelect the seeds you want to track:",
        "auto_stock_setup_gears": "🛠️ <b>Notification Setup: Gears</b>\n\nSelect the gears you want to track:",
        "status_on": "Enabled",
        "status_off": "Disabled",
        "add_channel_desc": "🤖 <b>Connect the bot to your channel</b>\n\n🔹 1. Click the button below\n🔹 2. Select your channel\n🔹 3. Give admin rights (required)\n\n🔗 The bot will automatically post legendary items in your channel!",
        "btn_add_channel": "🤖 Add to channel",
        "lang_select": "🌍 <b>Выберите ваш язык / Choose your language:</b>",
        "lang_set": "✅ Language set to: {lang}",
        "rarity_common": "Common",
        "rarity_uncommon": "Uncommon",
        "rarity_rare": "Rare",
        "rarity_epic": "Epic",
        "rarity_legendary": "Legendary",
        "rarity_mythic": "Mythic",
        "rarity_super": "Super",
        "rarity_secret": "Secret",
        "months": {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'},
    },
    'fr': {
        "main_header": "🌱 <b>Bourse Grow a Garden 2</b>\n\n",
        "select_action": "📊 Sélectionnez une action :",
        "btn_stock": "📊 Stock",
        "btn_predict": "🔮 Prédiction",
        "btn_weather": "🌤 Météo",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Connecter Canal",
        "btn_support": "🆘 Support",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Langue",
        "btn_back": "🔙 Retour",
        "btn_exit": "🚪 Quitter",
        "btn_seeds": "🌱 Graines",
        "btn_gears": "🛠️ Équipements",
        "btn_crates": "📦 Caisses",
        "btn_write": "✍️ Écrire",
        "btn_prev": "⬅️ Préc",
        "btn_next": "Suiv ➡️",
        "predict_header": "🔮 <b>Prédiction des Stocks</b>\n───────────────\n\nSélectionnez une catégorie :",
        "predict_no_data": "   <i>Aucune donnée pour les objets rares</i>\n\n",
        "predict_seeds_title": "GRAINES",
        "predict_gears_title": "ÉQUIPEMENTS",
        "predict_crates_title": "CAISSES",
        "stock_header": "📊 Stock Actuel\n────────────────────\n\n",
        "stock_no_items": "   ❌ Aucun objet\n",
        "stock_countdown": "\n⏱️ Stock : {time} (MSK)\n⏳ Temps restant : <b>{countdown}</b>",
        "timer_starting": "démarrage du chrono...",
        "timer_updating": "mise à jour du stock...",
        "weather_header": "🌤 <b>Météo & Heure</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Heure :</b> {time}\n",
        "weather_effect": "🌦 <b>Effet météo :</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Effet météo :</b> Clair\n",
        "weather_start": "⏱️ Début : {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Effet météo :</b> Aucune donnée\n",
        "moon_schedule": "📅 <b>Calendrier Lunaire :</b>\n",
        "moon_no_data": "🌙 <b>Cycle Lunaire :</b> Aucune prévision\n",
        "active_now": "actif",
        "in_mins": "dans {m}m",
        "morning": "🌅 Matin",
        "day": "☀️ Jour",
        "evening": "🌅 Soir",
        "night": "🌙 Nuit",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Abonnez-vous à notre canal pour accéder :\n{channel}\n\n",
        "sub_sponsors": "📢 <b>Et à nos sponsors :</b>\n",
        "sub_press_btn": "\n⬇️ Cliquez sur le bouton après l'abonnement.",
        "btn_subscribe": "📢 S'abonner au canal",
        "btn_check_sub": "✅ Vérifier l'abonnement",
        "sub_confirmed": "✅ <b>Abonnement confirmé !</b>\n\n🌱 Bienvenue !",
        "sub_failed": "❌ <b>Vous n'êtes pas abonné à tous les canaux !</b>\n\n",
        "sub_failed_alert": "❌ Abonnement non confirmé !",
        "sub_error_alert": "❌ Vous n'êtes pas abonné !",
        "support_header": "🆘 Support\n───────────────\n\n📌 Posez une question à un administrateur.\nÉcrivez votre message et nous vous répondrons.\n\n💬 Appuyez sur le bouton ci-dessous.",
        "support_write_msg": "✍️ Écrivez votre message\n\nDécrivez votre problème ou posez une question.\n<i>/cancel pour annuler</i>",
        "support_cancelled": "❌ Annulé",
        "support_sent": "✅ Envoyé !\n\nUn administrateur répondra bientôt.",
        "support_error": "❌ Erreur !\n\nVeuillez réessayer plus tard.",
        "auto_stock_desc": "⏱ <b>Notifications de Stock</b>\n\nLe bot vous enverra un message privé lorsque vos graines ou équipements sélectionnés seront en stock !\n\nChoisissez une catégorie :",
        "auto_stock_setup_seeds": "🌱 <b>Configuration : Graines</b>\n\nSélectionnez les graines à suivre :",
        "auto_stock_setup_gears": "🛠️ <b>Configuration : Équipements</b>\n\nSélectionnez les équipements à suivre :",
        "status_on": "Activé",
        "status_off": "Désactivé",
        "add_channel_desc": "🤖 <b>Connecter le bot à votre canal</b>\n\n🔹 1. Cliquez sur le bouton ci-dessous\n🔹 2. Sélectionnez votre canal\n🔹 3. Donnez les droits d'administration\n\n🔗 Le bot publiera automatiquement les objets légendaires !",
        "btn_add_channel": "🤖 Ajouter au canal",
        "lang_select": "🌍 <b>Choisissez votre langue :</b>",
        "lang_set": "✅ Langue définie : {lang}",
        "rarity_common": "Commun",
        "rarity_uncommon": "Peu Commun",
        "rarity_rare": "Rare",
        "rarity_epic": "Épique",
        "rarity_legendary": "Légendaire",
        "rarity_mythic": "Mythique",
        "rarity_super": "Super",
        "rarity_secret": "Secret",
        "months": {1: 'Jan', 2: 'Fév', 3: 'Mar', 4: 'Avr', 5: 'Mai', 6: 'Juin', 7: 'Juil', 8: 'Aoû', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Déc'},
    },
    'es': {
        "main_header": "🌱 <b>Bolsa Grow a Garden 2</b>\n\n",
        "select_action": "📊 Seleccione una acción:",
        "btn_stock": "📊 Stock",
        "btn_predict": "🔮 Predicción",
        "btn_weather": "🌤 Clima",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Conectar Canal",
        "btn_support": "🆘 Soporte",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Idioma",
        "btn_back": "🔙 Atrás",
        "btn_exit": "🚪 Salir",
        "btn_seeds": "🌱 Semillas",
        "btn_gears": "🛠️ Herramientas",
        "btn_crates": "📦 Cajas",
        "btn_write": "✍️ Escribir",
        "btn_prev": "⬅️ Ant",
        "btn_next": "Sig ➡️",
        "predict_header": "🔮 <b>Predicción de Stock</b>\n───────────────\n\nSeleccione una categoría:",
        "predict_no_data": "   <i>Sin datos para objetos raros</i>\n\n",
        "predict_seeds_title": "SEMILLAS",
        "predict_gears_title": "HERRAMIENTAS",
        "predict_crates_title": "CAJAS",
        "stock_header": "📊 Stock Actual\n────────────────────\n\n",
        "stock_no_items": "   ❌ Sin objetos\n",
        "stock_countdown": "\n⏱️ Stock: {time} (MSK)\n⏳ Tiempo restante: <b>{countdown}</b>",
        "timer_starting": "iniciando temporizador...",
        "timer_updating": "actualizando stock...",
        "weather_header": "🌤 <b>Clima y Hora</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Hora del día:</b> {time}\n",
        "weather_effect": "🌦 <b>Efecto del clima:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Efecto del clima:</b> Despejado\n",
        "weather_start": "⏱️ Inicio: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Efecto del clima:</b> Sin datos\n",
        "moon_schedule": "📅 <b>Calendario Lunar:</b>\n",
        "moon_no_data": "🌙 <b>Ciclo Lunar:</b> Sin previsiones\n",
        "active_now": "activo ahora",
        "in_mins": "en {m}m",
        "morning": "🌅 Mañana",
        "day": "☀️ Día",
        "evening": "🌅 Tarde",
        "night": "🌙 Noche",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Suscríbete a nuestro canal para acceder:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>Y a nuestros patrocinadores:</b>\n",
        "sub_press_btn": "\n⬇️ Presiona el botón después de suscribirte.",
        "btn_subscribe": "📢 Suscribirse al Canal",
        "btn_check_sub": "✅ Comprobar Suscripción",
        "sub_confirmed": "✅ <b>¡Suscripción confirmada!</b>\n\n🌱 ¡Bienvenido!",
        "sub_failed": "❌ <b>¡No estás suscrito a todos los canales!</b>\n\n",
        "sub_failed_alert": "❌ ¡Suscripción no confirmada!",
        "sub_error_alert": "❌ ¡No estás suscrito!",
        "support_header": "🆘 Soporte\n───────────────\n\n📌 Haz una pregunta a un administrador.\nEscribe tu mensaje y responderemos.\n\n💬 Presiona el botón de abajo.",
        "support_write_msg": "✍️ Escribe tu mensaje\n\nDescribe tu problema o haz una pregunta.\n<i>/cancel para cancelar</i>",
        "support_cancelled": "❌ Cancelado",
        "support_sent": "✅ ¡Enviado!\n\nUn administrador responderá pronto.",
        "support_error": "❌ ¡Error!\n\nInténtalo de nuevo más tarde.",
        "auto_stock_desc": "⏱ <b>Notificaciones Personales</b>\n\n¡El bot te enviará un mensaje cuando tus semillas o herramientas seleccionadas estén en stock!\n\nSelecciona una categoría:",
        "auto_stock_setup_seeds": "🌱 <b>Configuración: Semillas</b>\n\nSelecciona las semillas a seguir:",
        "auto_stock_setup_gears": "🛠️ <b>Configuración: Herramientas</b>\n\nSelecciona las herramientas a seguir:",
        "status_on": "Activado",
        "status_off": "Desactivado",
        "add_channel_desc": "🤖 <b>Conecta el bot a tu canal</b>\n\n🔹 1. Haz clic en el botón de abajo\n🔹 2. Selecciona tu canal\n🔹 3. Otorga permisos de admin\n\n🔗 ¡El bot publicará objetos legendarios automáticamente!",
        "btn_add_channel": "🤖 Añadir al canal",
        "lang_select": "🌍 <b>Elige tu idioma:</b>",
        "lang_set": "✅ Idioma configurado: {lang}",
        "rarity_common": "Común",
        "rarity_uncommon": "Poco Común",
        "rarity_rare": "Raro",
        "rarity_epic": "Épico",
        "rarity_legendary": "Legendario",
        "rarity_mythic": "Mítico",
        "rarity_super": "Súper",
        "rarity_secret": "Secreto",
        "months": {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'},
    },
    'it': {
        "main_header": "🌱 <b>Borsa Grow a Garden 2</b>\n\n",
        "select_action": "📊 Seleziona un'azione:",
        "btn_stock": "📊 Stock",
        "btn_predict": "🔮 Previsione",
        "btn_weather": "🌤 Meteo",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Collega Canale",
        "btn_support": "🆘 Supporto",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Lingua",
        "btn_back": "🔙 Indietro",
        "btn_exit": "🚪 Esci",
        "btn_seeds": "🌱 Semi",
        "btn_gears": "🛠️ Attrezzi",
        "btn_crates": "📦 Casse",
        "btn_write": "✍️ Scrivi",
        "btn_prev": "⬅️ Prec",
        "btn_next": "Succ ➡️",
        "predict_header": "🔮 <b>Previsione Stock</b>\n───────────────\n\nSeleziona una categoria:",
        "predict_no_data": "   <i>Nessun dato per oggetti rari</i>\n\n",
        "predict_seeds_title": "SEMI",
        "predict_gears_title": "ATTREZZI",
        "predict_crates_title": "CASSE",
        "stock_header": "📊 Stock Attuale\n────────────────────\n\n",
        "stock_no_items": "   ❌ Nessun oggetto\n",
        "stock_countdown": "\n⏱️ Stock: {time} (MSK)\n⏳ Tempo rimanente: <b>{countdown}</b>",
        "timer_starting": "avvio timer...",
        "timer_updating": "aggiornamento stock...",
        "weather_header": "🌤 <b>Meteo e Ora</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Fascia oraria:</b> {time}\n",
        "weather_effect": "🌦 <b>Effetto meteo:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Effetto meteo:</b> Sereno\n",
        "weather_start": "⏱️ Inizio: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Effetto meteo:</b> Nessun dato\n",
        "moon_schedule": "📅 <b>Calendario Lunare:</b>\n",
        "moon_no_data": "🌙 <b>Ciclo Lunare:</b> Nessuna previsione\n",
        "active_now": "attivo ora",
        "in_mins": "in {m}m",
        "morning": "🌅 Mattino",
        "day": "☀️ Giorno",
        "evening": "🌅 Sera",
        "night": "🌙 Notte",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Iscriviti al nostro canale per accedere:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>E ai nostri sponsor:</b>\n",
        "sub_press_btn": "\n⬇️ Premi il pulsante dopo esserti iscritto.",
        "btn_subscribe": "📢 Iscriviti al Canale",
        "btn_check_sub": "✅ Verifica Iscrizione",
        "sub_confirmed": "✅ <b>Iscrizione confermata!</b>\n\n🌱 Benvenuto!",
        "sub_failed": "❌ <b>Non sei iscritto a tutti i canali!</b>\n\n",
        "sub_failed_alert": "❌ Iscrizione non confermata!",
        "sub_error_alert": "❌ Non sei iscritto!",
        "support_header": "🆘 Supporto\n───────────────\n\n📌 Fai una domanda a un amministratore.\nScrivi il tuo messaggio e ti risponderemo.\n\n💬 Premi il pulsante qui sotto.",
        "support_write_msg": "✍️ Scrivi il tuo messaggio\n\nDescrivi il tuo problema o fai una domanda.\n<i>/cancel per annullare</i>",
        "support_cancelled": "❌ Annullato",
        "support_sent": "✅ Inviato!\n\nUn amministratore risponderà presto.",
        "support_error": "❌ Errore!\n\nRiprova più tardi.",
        "auto_stock_desc": "⏱ <b>Notifiche Personali</b>\n\nIl bot ti invierà un messaggio quando i semi o gli attrezzi scelti saranno disponibili!\n\nSeleziona una categoria:",
        "auto_stock_setup_seeds": "🌱 <b>Configurazione: Semi</b>\n\nSeleziona i semi da tracciare:",
        "auto_stock_setup_gears": "🛠️ <b>Configurazione: Attrezzi</b>\n\nSeleziona gli attrezzi da tracciare:",
        "status_on": "Attivo",
        "status_off": "Disattivo",
        "add_channel_desc": "🤖 <b>Collega il bot al tuo canale</b>\n\n🔹 1. Clicca il pulsante qui sotto\n🔹 2. Seleziona il tuo canale\n🔹 3. Dai i permessi di amministratore\n\n🔗 Il bot pubblicherà gli oggetti leggendari automaticamente!",
        "btn_add_channel": "🤖 Aggiungi al canale",
        "lang_select": "🌍 <b>Scegli la tua lingua:</b>",
        "lang_set": "✅ Lingua impostata: {lang}",
        "rarity_common": "Comune",
        "rarity_uncommon": "Non Comune",
        "rarity_rare": "Raro",
        "rarity_epic": "Epico",
        "rarity_legendary": "Leggendario",
        "rarity_mythic": "Mitico",
        "rarity_super": "Super",
        "rarity_secret": "Segreto",
        "months": {1: 'Gen', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'Mag', 6: 'Giu', 7: 'Lug', 8: 'Ago', 9: 'Set', 10: 'Ott', 11: 'Nov', 12: 'Dic'},
    },
    'de': {
        "main_header": "🌱 <b>Grow a Garden 2 Börse</b>\n\n",
        "select_action": "📊 Wähle eine Aktion:",
        "btn_stock": "📊 Stock",
        "btn_predict": "🔮 Vorhersage",
        "btn_weather": "🌤 Wetter",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Kanal verbinden",
        "btn_support": "🆘 Support",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Sprache",
        "btn_back": "🔙 Zurück",
        "btn_exit": "🚪 Beenden",
        "btn_seeds": "🌱 Samen",
        "btn_gears": "🛠️ Werkzeuge",
        "btn_crates": "📦 Kisten",
        "btn_write": "✍️ Schreiben",
        "btn_prev": "⬅️ Zurück",
        "btn_next": "Weiter ➡️",
        "predict_header": "🔮 <b>Stock Vorhersage</b>\n───────────────\n\nWähle eine Kategorie:",
        "predict_no_data": "   <i>Keine Daten für seltene Gegenstände</i>\n\n",
        "predict_seeds_title": "SAMEN",
        "predict_gears_title": "WERKZEUGE",
        "predict_crates_title": "KISTEN",
        "stock_header": "📊 Aktueller Stock\n────────────────────\n\n",
        "stock_no_items": "   ❌ Keine Gegenstände\n",
        "stock_countdown": "\n⏱️ Stock: {time} (MSK)\n⏳ Verbleibend: <b>{countdown}</b>",
        "timer_starting": "Timer startet...",
        "timer_updating": "Stock aktualisiert...",
        "weather_header": "🌤 <b>Wetter & Zeit</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Tageszeit:</b> {time}\n",
        "weather_effect": "🌦 <b>Wettereffekt:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Wettereffekt:</b> Klar\n",
        "weather_start": "⏱️ Beginn: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Wettereffekt:</b> Keine Daten\n",
        "moon_schedule": "📅 <b>Mondkalender:</b>\n",
        "moon_no_data": "🌙 <b>Mondzyklus:</b> Keine Vorhersage\n",
        "active_now": "jetzt aktiv",
        "in_mins": "in {m}m",
        "morning": "🌅 Morgen",
        "day": "☀️ Tag",
        "evening": "🌅 Abend",
        "night": "🌙 Nacht",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Abonniere unseren Kanal für Zugang:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>Und unsere Sponsoren:</b>\n",
        "sub_press_btn": "\n⬇️ Drücke den Button nach dem Abonnieren.",
        "btn_subscribe": "📢 Kanal abonnieren",
        "btn_check_sub": "✅ Abo prüfen",
        "sub_confirmed": "✅ <b>Abonnement bestätigt!</b>\n\n🌱 Willkommen!",
        "sub_failed": "❌ <b>Du hast nicht alle Kanäle abonniert!</b>\n\n",
        "sub_failed_alert": "❌ Abo nicht bestätigt!",
        "sub_error_alert": "❌ Du bist nicht abonniert!",
        "support_header": "🆘 Support\n───────────────\n\n📌 Stelle einem Admin eine Frage.\nSchreibe deine Nachricht, wir antworten.\n\n💬 Klicke den Button unten.",
        "support_write_msg": "✍️ Schreibe deine Nachricht\n\nBeschreibe dein Problem.\n<i>/cancel zum Abbrechen</i>",
        "support_cancelled": "❌ Abgebrochen",
        "support_sent": "✅ Gesendet!\n\nEin Admin antwortet in Kürze.",
        "support_error": "❌ Fehler!\n\nBitte später erneut versuchen.",
        "auto_stock_desc": "⏱ <b>Persönliche Benachrichtigungen</b>\n\nDer Bot sendet dir eine Nachricht, wenn deine Samen oder Werkzeuge auf Lager sind!\n\nWähle eine Kategorie:",
        "auto_stock_setup_seeds": "🌱 <b>Setup: Samen</b>\n\nWähle Samen zum Verfolgen:",
        "auto_stock_setup_gears": "🛠️ <b>Setup: Werkzeuge</b>\n\nWähle Werkzeuge zum Verfolgen:",
        "status_on": "Aktiviert",
        "status_off": "Deaktiviert",
        "add_channel_desc": "🤖 <b>Bot mit Kanal verbinden</b>\n\n🔹 1. Klicke unten\n🔹 2. Wähle deinen Kanal\n🔹 3. Gib Admin-Rechte\n\n🔗 Der Bot postet legendäre Gegenstände!",
        "btn_add_channel": "🤖 Zum Kanal hinzufügen",
        "lang_select": "🌍 <b>Wähle deine Sprache:</b>",
        "lang_set": "✅ Sprache eingestellt auf: {lang}",
        "rarity_common": "Gewöhnlich",
        "rarity_uncommon": "Ungewöhnlich",
        "rarity_rare": "Selten",
        "rarity_epic": "Episch",
        "rarity_legendary": "Legendär",
        "rarity_mythic": "Mythisch",
        "rarity_super": "Super",
        "rarity_secret": "Geheim",
        "months": {1: 'Jan', 2: 'Feb', 3: 'Mär', 4: 'Apr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Okt', 11: 'Nov', 12: 'Dez'},
    },
    'pt': {
        "main_header": "🌱 <b>Bolsa Grow a Garden 2</b>\n\n",
        "select_action": "📊 Escolha uma ação:",
        "btn_stock": "📊 Estoque",
        "btn_predict": "🔮 Previsão",
        "btn_weather": "🌤 Clima",
        "btn_autostock": "⏱ Auto-Stock",
        "btn_channel": "📢 Conectar Canal",
        "btn_support": "🆘 Suporte",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Idioma",
        "btn_back": "🔙 Voltar",
        "btn_exit": "🚪 Sair",
        "btn_seeds": "🌱 Sementes",
        "btn_gears": "🛠️ Ferramentas",
        "btn_crates": "📦 Caixas",
        "btn_write": "✍️ Escrever",
        "btn_prev": "⬅️ Ant",
        "btn_next": "Seg ➡️",
        "predict_header": "🔮 <b>Previsão de Estoque</b>\n───────────────\n\nEscolha uma categoria:",
        "predict_no_data": "   <i>Sem dados para itens raros</i>\n\n",
        "predict_seeds_title": "SEMENTES",
        "predict_gears_title": "FERRAMENTAS",
        "predict_crates_title": "CAIXAS",
        "stock_header": "📊 Estoque Atual\n────────────────────\n\n",
        "stock_no_items": "   ❌ Sem itens\n",
        "stock_countdown": "\n⏱️ Estoque: {time} (MSK)\n⏳ Tempo restante: <b>{countdown}</b>",
        "timer_starting": "iniciando cronômetro...",
        "timer_updating": "atualizando estoque...",
        "weather_header": "🌤 <b>Clima e Hora</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Hora do dia:</b> {time}\n",
        "weather_effect": "🌦 <b>Efeito do clima:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Efeito do clima:</b> Limpo\n",
        "weather_start": "⏱️ Início: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Efeito do clima:</b> Sem dados\n",
        "moon_schedule": "📅 <b>Calendário Lunar:</b>\n",
        "moon_no_data": "🌙 <b>Ciclo Lunar:</b> Sem previsões\n",
        "active_now": "ativo agora",
        "in_mins": "em {m}m",
        "morning": "🌅 Manhã",
        "day": "☀️ Dia",
        "evening": "🌅 Tarde",
        "night": "🌙 Noite",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Inscreva-se no nosso canal para acessar:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>E nos nossos patrocinadores:</b>\n",
        "sub_press_btn": "\n⬇️ Pressione o botão após se inscrever.",
        "btn_subscribe": "📢 Inscrever-se",
        "btn_check_sub": "✅ Verificar Inscrição",
        "sub_confirmed": "✅ <b>Inscrição confirmada!</b>\n\n🌱 Bem-vindo!",
        "sub_failed": "❌ <b>Você não se inscreveu em todos os canais!</b>\n\n",
        "sub_failed_alert": "❌ Inscrição não confirmada!",
        "sub_error_alert": "❌ Você não está inscrito!",
        "support_header": "🆘 Suporte\n───────────────\n\n📌 Faça uma pergunta a um admin.\nEscreva sua mensagem e nós responderemos.\n\n💬 Pressione o botão abaixo.",
        "support_write_msg": "✍️ Escreva sua mensagem\n\nDescreva seu problema.\n<i>/cancel para cancelar</i>",
        "support_cancelled": "❌ Cancelado",
        "support_sent": "✅ Enviado!\n\nUm admin responderá em breve.",
        "support_error": "❌ Erro!\n\nTente novamente mais tarde.",
        "auto_stock_desc": "⏱ <b>Notificações Pessoais</b>\n\nO bot enviará uma mensagem quando suas sementes ou ferramentas estiverem em estoque!\n\nEscolha uma categoria:",
        "auto_stock_setup_seeds": "🌱 <b>Configuração: Sementes</b>\n\nEscolha as sementes para rastrear:",
        "auto_stock_setup_gears": "🛠️ <b>Configuração: Ferramentas</b>\n\nEscolha as ferramentas para rastrear:",
        "status_on": "Ativado",
        "status_off": "Desativado",
        "add_channel_desc": "🤖 <b>Conecte o bot ao seu canal</b>\n\n🔹 1. Clique abaixo\n🔹 2. Escolha seu canal\n🔹 3. Dê permissões de admin\n\n🔗 O bot postará itens lendários automaticamente!",
        "btn_add_channel": "🤖 Adicionar ao canal",
        "lang_select": "🌍 <b>Escolha seu idioma:</b>",
        "lang_set": "✅ Idioma configurado: {lang}",
        "rarity_common": "Comum",
        "rarity_uncommon": "Incomum",
        "rarity_rare": "Raro",
        "rarity_epic": "Épico",
        "rarity_legendary": "Lendário",
        "rarity_mythic": "Mítico",
        "rarity_super": "Super",
        "rarity_secret": "Secreto",
        "months": {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'},
    },
    'tr': {
        "main_header": "🌱 <b>Grow a Garden 2 Borsa</b>\n\n",
        "select_action": "📊 Bir işlem seçin:",
        "btn_stock": "📊 Stok",
        "btn_predict": "🔮 Tahmin",
        "btn_weather": "🌤 Hava",
        "btn_autostock": "⏱ Oto-Stok",
        "btn_channel": "📢 Kanal Bağla",
        "btn_support": "🆘 Destek",
        "btn_admin": "⚙️ Admin",
        "btn_language": "🌍 Dil",
        "btn_back": "🔙 Geri",
        "btn_exit": "🚪 Çıkış",
        "btn_seeds": "🌱 Tohumlar",
        "btn_gears": "🛠️ Aletler",
        "btn_crates": "📦 Kasalar",
        "btn_write": "✍️ Yaz",
        "btn_prev": "⬅️ Önceki",
        "btn_next": "Sonraki ➡️",
        "predict_header": "🔮 <b>Stok Tahmini</b>\n───────────────\n\nBir kategori seçin:",
        "predict_no_data": "   <i>Nadir eşya verisi yok</i>\n\n",
        "predict_seeds_title": "TOHUMLAR",
        "predict_gears_title": "ALETLER",
        "predict_crates_title": "KASALAR",
        "stock_header": "📊 Mevcut Stok\n────────────────────\n\n",
        "stock_no_items": "   ❌ Eşya yok\n",
        "stock_countdown": "\n⏱️ Stok: {time} (MSK)\n⏳ Kalan zaman: <b>{countdown}</b>",
        "timer_starting": "sayaç başlıyor...",
        "timer_updating": "stok güncelleniyor...",
        "weather_header": "🌤 <b>Hava & Zaman</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>Günün vakti:</b> {time}\n",
        "weather_effect": "🌦 <b>Hava etkisi:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>Hava etkisi:</b> Açık\n",
        "weather_start": "⏱️ Başlangıç: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>Hava etkisi:</b> Veri yok\n",
        "moon_schedule": "📅 <b>Ay Takvimi:</b>\n",
        "moon_no_data": "🌙 <b>Ay Döngüsü:</b> Tahmin verisi yok\n",
        "active_now": "şu an aktif",
        "in_mins": "{m} dk içinde",
        "morning": "🌅 Sabah",
        "day": "☀️ Gündüz",
        "evening": "🌅 Akşam",
        "night": "🌙 Gece",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 Erişmek için kanalımıza abone olun:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>Ve sponsorlarımıza:</b>\n",
        "sub_press_btn": "\n⬇️ Abone olduktan sonra düğmeye basın.",
        "btn_subscribe": "📢 Kanala Abone Ol",
        "btn_check_sub": "✅ Aboneliği Kontrol Et",
        "sub_confirmed": "✅ <b>Abonelik onaylandı!</b>\n\n🌱 Hoş geldiniz!",
        "sub_failed": "❌ <b>Tüm kanallara abone değilsiniz!</b>\n\n",
        "sub_failed_alert": "❌ Abonelik onaylanmadı!",
        "sub_error_alert": "❌ Abone değilsiniz!",
        "support_header": "🆘 Destek\n───────────────\n\n📌 Bir yöneticiye soru sorun.\nMesajınızı yazın, cevaplayalım.\n\n💬 Aşağıdaki düğmeye basın.",
        "support_write_msg": "✍️ Mesajınızı yazın\n\nSorununuzu açıklayın.\n<i>/cancel ile iptal edin</i>",
        "support_cancelled": "❌ İptal edildi",
        "support_sent": "✅ Gönderildi!\n\nBir yönetici yakında cevap verecek.",
        "support_error": "❌ Hata!\n\nLütfen daha sonra tekrar deneyin.",
        "auto_stock_desc": "⏱ <b>Kişisel Stok Bildirimleri</b>\n\nSeçtiğiniz tohumlar veya aletler stoğa girdiğinde bot size mesaj gönderecek!\n\nKategori seçin:",
        "auto_stock_setup_seeds": "🌱 <b>Ayar: Tohumlar</b>\n\nTakip edilecek tohumları seçin:",
        "auto_stock_setup_gears": "🛠️ <b>Ayar: Aletler</b>\n\nTakip edilecek aletleri seçin:",
        "status_on": "Açık",
        "status_off": "Kapalı",
        "add_channel_desc": "🤖 <b>Botu kanalınıza bağlayın</b>\n\n🔹 1. Aşağıya tıklayın\n🔹 2. Kanalınızı seçin\n🔹 3. Yönetici izni verin\n\n🔗 Bot efsanevi eşyaları otomatik paylaşacak!",
        "btn_add_channel": "🤖 Kanala ekle",
        "lang_select": "🌍 <b>Dilinizi seçin:</b>",
        "lang_set": "✅ Dil ayarlandı: {lang}",
        "rarity_common": "Sıradan",
        "rarity_uncommon": "Olağandışı",
        "rarity_rare": "Nadir",
        "rarity_epic": "Destansı",
        "rarity_legendary": "Efsanevi",
        "rarity_mythic": "Mistik",
        "rarity_super": "Süper",
        "rarity_secret": "Gizli",
        "months": {1: 'Oca', 2: 'Şub', 3: 'Mar', 4: 'Nis', 5: 'May', 6: 'Haz', 7: 'Tem', 8: 'Ağu', 9: 'Eyl', 10: 'Eki', 11: 'Kas', 12: 'Ara'},
    },
    'ar': {
        "main_header": "🌱 <b>بورصة Grow a Garden 2</b>\n\n",
        "select_action": "📊 اختر إجراء:",
        "btn_stock": "📊 المخزون",
        "btn_predict": "🔮 توقع",
        "btn_weather": "🌤 الطقس",
        "btn_autostock": "⏱ تنبيه تلقائي",
        "btn_channel": "📢 ربط القناة",
        "btn_support": "🆘 دعم",
        "btn_admin": "⚙️ أدمن",
        "btn_language": "🌍 اللغة",
        "btn_back": "🔙 عودة",
        "btn_exit": "🚪 خروج",
        "btn_seeds": "🌱 بذور",
        "btn_gears": "🛠️ أدوات",
        "btn_crates": "📦 صناديق",
        "btn_write": "✍️ اكتب",
        "btn_prev": "⬅️ السابق",
        "btn_next": "التالي ➡️",
        "predict_header": "🔮 <b>توقع المخزون</b>\n───────────────\n\nاختر فئة:",
        "predict_no_data": "   <i>لا توجد بيانات للعناصر النادرة</i>\n\n",
        "predict_seeds_title": "بذور",
        "predict_gears_title": "أدوات",
        "predict_crates_title": "صناديق",
        "stock_header": "📊 المخزون الحالي\n────────────────────\n\n",
        "stock_no_items": "   ❌ لا توجد عناصر\n",
        "stock_countdown": "\n⏱️ المخزون: {time} (MSK)\n⏳ الوقت المتبقي: <b>{countdown}</b>",
        "timer_starting": "بدء المؤقت...",
        "timer_updating": "تحديث المخزون...",
        "weather_header": "🌤 <b>الطقس والوقت</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>الوقت من اليوم:</b> {time}\n",
        "weather_effect": "🌦 <b>تأثير الطقس:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>تأثير الطقس:</b> صافي\n",
        "weather_start": "⏱️ بدأ في: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>تأثير الطقس:</b> لا توجد بيانات\n",
        "moon_schedule": "📅 <b>جدول القمر:</b>\n",
        "moon_no_data": "🌙 <b>دورة القمر:</b> لا توجد توقعات\n",
        "active_now": "نشط الآن",
        "in_mins": "في {m} دقيقة",
        "morning": "🌅 الصباح",
        "day": "☀️ النهار",
        "evening": "🌅 المساء",
        "night": "🌙 الليل",
        "sub_required": "🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n📢 يرجى الاشتراك في قناتنا للوصول:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>ولرعاتنا:</b>\n",
        "sub_press_btn": "\n⬇️ اضغط على الزر أدناه بعد الاشتراك.",
        "btn_subscribe": "📢 اشتراك في القناة",
        "btn_check_sub": "✅ تحقق من الاشتراك",
        "sub_confirmed": "✅ <b>تم تأكيد الاشتراك!</b>\n\n🌱 أهلاً بك!",
        "sub_failed": "❌ <b>لم تشترك في جميع القنوات!</b>\n\n",
        "sub_failed_alert": "❌ الاشتراك غير مؤكد!",
        "sub_error_alert": "❌ أنت غير مشترك!",
        "support_header": "🆘 الدعم\n───────────────\n\n📌 اطرح سؤالاً على المسؤول.\nاكتب رسالتك وسنقوم بالرد.\n\n💬 اضغط على الزر أدناه.",
        "support_write_msg": "✍️ اكتب رسالتك\n\nصف مشكلتك أو اطرح سؤالاً.\n<i>أرسل /cancel للإلغاء</i>",
        "support_cancelled": "❌ تم الإلغاء",
        "support_sent": "✅ تم الإرسال!\n\nسيقوم مسؤول بالرد قريباً.",
        "support_error": "❌ خطأ!\n\nيرجى المحاولة مرة أخرى لاحقاً.",
        "auto_stock_desc": "⏱ <b>إشعارات المخزون الشخصية</b>\n\nسيرسل لك البوت رسائل خاصة عندما تتوفر البذور أو الأدوات المحددة!\n\nاختر فئة للإعداد:",
        "auto_stock_setup_seeds": "🌱 <b>إعداد الإشعارات: البذور</b>\n\nحدد البذور التي تريد تتبعها:",
        "auto_stock_setup_gears": "🛠️ <b>إعداد الإشعارات: الأدوات</b>\n\nحدد الأدوات التي تريد تتبعها:",
        "status_on": "مفعل",
        "status_off": "معطل",
        "add_channel_desc": "🤖 <b>ربط البوت بقناتك</b>\n\n🔹 1. انقر على الزر أدناه\n🔹 2. اختر قناتك\n🔹 3. أعط صلاحيات المسؤول\n\n🔗 سينشر البوت العناصر الأسطورية تلقائياً!",
        "btn_add_channel": "🤖 إضافة للقناة",
        "lang_select": "🌍 <b>اختر لغتك:</b>",
        "lang_set": "✅ تم تعيين اللغة: {lang}",
        "rarity_common": "شائع",
        "rarity_uncommon": "غير شائع",
        "rarity_rare": "نادر",
        "rarity_epic": "ملحمي",
        "rarity_legendary": "أسطوري",
        "rarity_mythic": "خرافي",
        "rarity_super": "سوبر",
        "rarity_secret": "سري",
        "months": {1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'},
    },
    'zh': {
        "main_header": "🌱 <b>Grow a Garden 2 交易所</b>\n\n",
        "select_action": "📊 请选择操作：",
        "btn_stock": "📊 库存",
        "btn_predict": "🔮 预测",
        "btn_weather": "🌤 天气",
        "btn_autostock": "⏱ 自动库存",
        "btn_channel": "📢 连接频道",
        "btn_support": "🆘 支持",
        "btn_admin": "⚙️ 管理",
        "btn_language": "🌍 语言",
        "btn_back": "🔙 返回",
        "btn_exit": "🚪 退出",
        "btn_seeds": "🌱 种子",
        "btn_gears": "🛠️ 工具",
        "btn_crates": "📦 箱子",
        "btn_write": "✍️ 编写",
        "btn_prev": "⬅️ 上一页",
        "btn_next": "下一页 ➡️",
        "predict_header": "🔮 <b>库存预测</b>\n───────────────\n\n请选择类别：",
        "predict_no_data": "   <i>稀有物品暂无数据</i>\n\n",
        "predict_seeds_title": "种子",
        "predict_gears_title": "工具",
        "predict_crates_title": "箱子",
        "stock_header": "📊 当前库存\n────────────────────\n\n",
        "stock_no_items": "   ❌ 无物品\n",
        "stock_countdown": "\n⏱️ 库存：{time} (MSK)\n⏳ 剩余时间：<b>{countdown}</b>",
        "timer_starting": "计时开始...",
        "timer_updating": "库存更新中...",
        "weather_header": "🌤 <b>天气与时间</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>当前时间：</b> {time}\n",
        "weather_effect": "🌦 <b>天气效果：</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>天气效果：</b> 晴朗\n",
        "weather_start": "⏱️ 开始时间：{time} (MSK)\n",
        "weather_no_data": "🌦 <b>天气效果：</b> 无数据\n",
        "moon_schedule": "📅 <b>月相日程：</b>\n",
        "moon_no_data": "🌙 <b>月相：</b> 无预测数据\n",
        "active_now": "当前激活",
        "in_mins": "{m}分钟后",
        "morning": "🌅 早晨",
        "day": "☀️ 白天",
        "evening": "🌅 傍晚",
        "night": "🌙 夜晚",
        "sub_required": "🌱 <b>Grow a Garden 2 机器人</b>\n\n📢 请订阅我们的频道以获得访问权限：\n{channel}\n\n",
        "sub_sponsors": "📢 <b>及我们的赞助商：</b>\n",
        "sub_press_btn": "\n⬇️ 订阅后请按下方按钮。",
        "btn_subscribe": "📢 订阅频道",
        "btn_check_sub": "✅ 检查订阅",
        "sub_confirmed": "✅ <b>订阅已确认！</b>\n\n🌱 欢迎！",
        "sub_failed": "❌ <b>您未订阅所有频道！</b>\n\n",
        "sub_failed_alert": "❌ 订阅未确认！",
        "sub_error_alert": "❌ 您尚未订阅！",
        "support_header": "🆘 支持\n───────────────\n\n📌 向管理员提问。\n编写您的消息，我们会尽快回复。\n\n💬 请点击下方按钮。",
        "support_write_msg": "✍️ 编写您的消息\n\n描述您的问题或提问。\n<i>发送 /cancel 取消</i>",
        "support_cancelled": "❌ 已取消",
        "support_sent": "✅ 已发送！\n\n管理员很快会回复。",
        "support_error": "❌ 错误！\n\n请稍后再试。",
        "auto_stock_desc": "⏱ <b>个人库存通知</b>\n\n当您选择的种子或工具上架时，机器人将向您发送私信！\n\n请选择类别进行设置：",
        "auto_stock_setup_seeds": "🌱 <b>通知设置：种子</b>\n\n选择要跟踪的种子：",
        "auto_stock_setup_gears": "🛠️ <b>通知设置：工具</b>\n\n选择要跟踪的工具：",
        "status_on": "已启用",
        "status_off": "已禁用",
        "add_channel_desc": "🤖 <b>将机器人连接到您的频道</b>\n\n🔹 1. 点击下方按钮\n🔹 2. 选择您的频道\n🔹 3. 授予管理员权限\n\n🔗 机器人将自动发布传说物品！",
        "btn_add_channel": "🤖 添加到频道",
        "lang_select": "🌍 <b>选择您的语言：</b>",
        "lang_set": "✅ 语言已设为：{lang}",
        "rarity_common": "普通",
        "rarity_uncommon": "罕见",
        "rarity_rare": "稀有",
        "rarity_epic": "史诗",
        "rarity_legendary": "传说",
        "rarity_mythic": "神话",
        "rarity_super": "超级",
        "rarity_secret": "秘密",
        "months": {1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月', 7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'},
    },
    'ja': {
        "main_header": "🌱 <b>Grow a Garden 2 取引所</b>\n\n",
        "select_action": "📊 アクションを選択：",
        "btn_stock": "📊 在庫",
        "btn_predict": "🔮 予測",
        "btn_weather": "🌤 天気",
        "btn_autostock": "⏱ 自動在庫",
        "btn_channel": "📢 チャンネル連携",
        "btn_support": "🆘 サポート",
        "btn_admin": "⚙️ 管理者",
        "btn_language": "🌍 言語",
        "btn_back": "🔙 戻る",
        "btn_exit": "🚪 終了",
        "btn_seeds": "🌱 種",
        "btn_gears": "🛠️ 道具",
        "btn_crates": "📦 クレート",
        "btn_write": "✍️ 書く",
        "btn_prev": "⬅️ 前",
        "btn_next": "次 ➡️",
        "predict_header": "🔮 <b>在庫予測</b>\n───────────────\n\nカテゴリーを選択：",
        "predict_no_data": "   <i>レアアイテムのデータなし</i>\n\n",
        "predict_seeds_title": "種",
        "predict_gears_title": "道具",
        "predict_crates_title": "クレート",
        "stock_header": "📊 現在の在庫\n────────────────────\n\n",
        "stock_no_items": "   ❌ アイテムなし\n",
        "stock_countdown": "\n⏱️ 在庫：{time} (MSK)\n⏳ 残り時間：<b>{countdown}</b>",
        "timer_starting": "タイマー開始...",
        "timer_updating": "在庫更新中...",
        "weather_header": "🌤 <b>天気と時間</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>時間帯：</b> {time}\n",
        "weather_effect": "🌦 <b>天気効果：</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>天気効果：</b> 晴れ\n",
        "weather_start": "⏱️ 開始：{time} (MSK)\n",
        "weather_no_data": "🌦 <b>天気効果：</b> データなし\n",
        "moon_schedule": "📅 <b>月のスケジュール：</b>\n",
        "moon_no_data": "🌙 <b>月周期：</b> 予測データなし\n",
        "active_now": "現在有効",
        "in_mins": "{m}分後",
        "morning": "🌅 朝",
        "day": "☀️ 昼",
        "evening": "🌅 夕方",
        "night": "🌙 夜",
        "sub_required": "🌱 <b>Grow a Garden 2 Bot</b>\n\n📢 アクセスするにはチャンネルを登録してください：\n{channel}\n\n",
        "sub_sponsors": "📢 <b>およびスポンサー：</b>\n",
        "sub_press_btn": "\n⬇️ 登録後、下のボタンを押してください。",
        "btn_subscribe": "📢 チャンネル登録",
        "btn_check_sub": "✅ 登録を確認",
        "sub_confirmed": "✅ <b>登録確認済み！</b>\n\n🌱 ようこそ！",
        "sub_failed": "❌ <b>すべてのチャンネルに登録していません！</b>\n\n",
        "sub_failed_alert": "❌ 登録が確認できません！",
        "sub_error_alert": "❌ 登録していません！",
        "support_header": "🆘 サポート\n───────────────\n\n📌 管理者に質問する。\nメッセージを書いてください。\n\n💬 下のボタンを押してください。",
        "support_write_msg": "✍️ メッセージを書く\n\n問題や質問を記述してください。\n<i>/cancel でキャンセル</i>",
        "support_cancelled": "❌ キャンセルしました",
        "support_sent": "✅ 送信完了！\n\n管理者がすぐに返信します。",
        "support_error": "❌ エラー！\n\n後でもう一度お試しください。",
        "auto_stock_desc": "⏱ <b>個人在庫通知</b>\n\n選択した種や道具が入荷した時にBotがメッセージを送ります！\n\nカテゴリーを選択：",
        "auto_stock_setup_seeds": "🌱 <b>通知設定：種</b>\n\n追跡する種を選択：",
        "auto_stock_setup_gears": "🛠️ <b>通知設定：道具</b>\n\n追跡する道具を選択：",
        "status_on": "有効",
        "status_off": "無効",
        "add_channel_desc": "🤖 <b>Botをチャンネルに連携</b>\n\n🔹 1. 下のボタンをクリック\n🔹 2. チャンネルを選択\n🔹 3. 管理者権限を付与\n\n🔗 伝説のアイテムを自動投稿します！",
        "btn_add_channel": "🤖 チャンネルに追加",
        "lang_select": "🌍 <b>言語を選択してください：</b>",
        "lang_set": "✅ 言語を設定しました：{lang}",
        "rarity_common": "コモン",
        "rarity_uncommon": "アンコモン",
        "rarity_rare": "レア",
        "rarity_epic": "エピック",
        "rarity_legendary": "レジェンダリー",
        "rarity_mythic": "ミシック",
        "rarity_super": "スーパー",
        "rarity_secret": "シークレット",
        "months": {1: '1月', 2: '2月', 3: '3月', 4: '4月', 5: '5月', 6: '6月', 7: '7月', 8: '8月', 9: '9月', 10: '10月', 11: '11月', 12: '12月'},
    },
    'ko': {
        "main_header": "🌱 <b>Grow a Garden 2 거래소</b>\n\n",
        "select_action": "📊 작업 선택:",
        "btn_stock": "📊 재고",
        "btn_predict": "🔮 예측",
        "btn_weather": "🌤 날씨",
        "btn_autostock": "⏱ 자동 재고",
        "btn_channel": "📢 채널 연결",
        "btn_support": "🆘 지원",
        "btn_admin": "⚙️ 관리자",
        "btn_language": "🌍 언어",
        "btn_back": "🔙 뒤로",
        "btn_exit": "🚪 종료",
        "btn_seeds": "🌱 씨앗",
        "btn_gears": "🛠️ 도구",
        "btn_crates": "📦 상자",
        "btn_write": "✍️ 쓰기",
        "btn_prev": "⬅️ 이전",
        "btn_next": "다음 ➡️",
        "predict_header": "🔮 <b>재고 예측</b>\n───────────────\n\n카테고리 선택:",
        "predict_no_data": "   <i>희귀 아이템 데이터 없음</i>\n\n",
        "predict_seeds_title": "씨앗",
        "predict_gears_title": "도구",
        "predict_crates_title": "상자",
        "stock_header": "📊 현재 재고\n────────────────────\n\n",
        "stock_no_items": "   ❌ 아이템 없음\n",
        "stock_countdown": "\n⏱️ 재고: {time} (MSK)\n⏳ 남은 시간: <b>{countdown}</b>",
        "timer_starting": "타이머 시작 중...",
        "timer_updating": "재고 업데이트 중...",
        "weather_header": "🌤 <b>날씨 및 시간</b>\n────────────────────\n\n",
        "time_of_day": "🕐 <b>시간대:</b> {time}\n",
        "weather_effect": "🌦 <b>날씨 효과:</b> {emoji} {effect}\n",
        "weather_clear": "☀️ <b>날씨 효과:</b> 맑음\n",
        "weather_start": "⏱️ 시작: {time} (MSK)\n",
        "weather_no_data": "🌦 <b>날씨 효과:</b> 데이터 없음\n",
        "moon_schedule": "📅 <b>달력:</b>\n",
        "moon_no_data": "🌙 <b>달 주기:</b> 예측 데이터 없음\n",
        "active_now": "현재 활성",
        "in_mins": "{m}분 후",
        "morning": "🌅 아침",
        "day": "☀️ 낮",
        "evening": "🌅 저녁",
        "night": "🌙 밤",
        "sub_required": "🌱 <b>Grow a Garden 2 봇</b>\n\n📢 채널을 구독해야 접속할 수 있습니다:\n{channel}\n\n",
        "sub_sponsors": "📢 <b>그리고 스폰서 채널:</b>\n",
        "sub_press_btn": "\n⬇️ 구독 후 아래 버튼을 누르세요.",
        "btn_subscribe": "📢 채널 구독",
        "btn_check_sub": "✅ 구독 확인",
        "sub_confirmed": "✅ <b>구독 확인 완료!</b>\n\n🌱 환영합니다!",
        "sub_failed": "❌ <b>모든 채널을 구독하지 않았습니다!</b>\n\n",
        "sub_failed_alert": "❌ 구독이 확인되지 않았습니다!",
        "sub_error_alert": "❌ 구독하지 않았습니다!",
        "support_header": "🆘 지원\n───────────────\n\n📌 관리자에게 질문하기.\n메시지를 남겨주시면 답변해 드립니다.\n\n💬 아래 버튼을 누르세요.",
        "support_write_msg": "✍️ 메시지 작성\n\n문제나 질문을 설명해주세요.\n<i>/cancel 로 취소</i>",
        "support_cancelled": "❌ 취소됨",
        "support_sent": "✅ 전송 완료!\n\n관리자가 곧 답변할 것입니다.",
        "support_error": "❌ 오류!\n\n나중에 다시 시도해주세요.",
        "auto_stock_desc": "⏱ <b>개인 재고 알림</b>\n\n선택한 씨앗이나 도구가 입고되면 봇이 메시지를 보냅니다!\n\n설정할 카테고리 선택:",
        "auto_stock_setup_seeds": "🌱 <b>알림 설정: 씨앗</b>\n\n추적할 씨앗을 선택하세요:",
        "auto_stock_setup_gears": "🛠️ <b>알림 설정: 도구</b>\n\n추적할 도구를 선택하세요:",
        "status_on": "활성화됨",
        "status_off": "비활성화됨",
        "add_channel_desc": "🤖 <b>봇을 채널에 연결</b>\n\n🔹 1. 아래 버튼 클릭\n🔹 2. 채널 선택\n🔹 3. 관리자 권 부여\n\n🔗 봇이 전설 아이템을 자동으로 게시합니다!",
        "btn_add_channel": "🤖 채널에 추가",
        "lang_select": "🌍 <b>언어를 선택하세요:</b>",
        "lang_set": "✅ 언어가 설정되었습니다: {lang}",
        "rarity_common": "일반",
        "rarity_uncommon": "고급",
        "rarity_rare": "희귀",
        "rarity_epic": "영웅",
        "rarity_legendary": "전설",
        "rarity_mythic": "신화",
        "rarity_super": "슈퍼",
        "rarity_secret": "비밀",
        "months": {1: '1월', 2: '2월', 3: '3월', 4: '4월', 5: '5월', 6: '6월', 7: '7월', 8: '8월', 9: '9월', 10: '10월', 11: '11월', 12: '12월'},
    },
}

def get_t(lang: str, key: str, **kwargs) -> str:
    """Helper to get translated string and format it if kwargs are provided."""
    if not lang or lang not in TRANSLATIONS:
        lang = "en"

    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

def get_rarity_name_t(rarity: str, lang: str) -> str:
    """Get translated rarity name."""
    rarity_lower = rarity.lower()
    key = f"rarity_{rarity_lower}"
    translated = get_t(lang, key)

    if translated == key:
        return rarity.capitalize()
    return translated


BOT_TOKEN = os.getenv("BOT_TOKEN", "8292483950:AAEpeXQm6EYmVc9pP29W9Q1NJgFS2YZDmNk")
CHANNEL_ID = "@Zendeks_rblx"
ADMIN_IDS = [6668784806, 8972052372]

DATA_FILE = "bot_data.json"
CHECK_CACHE_TIME = 60
API_BASE = "https://api.growagarden2stock.com"
POLL_INTERVAL = 30
RESTOCK_INTERVAL = 270

BOT_LINK = "https://t.me/growagarden2stock_tetrisbot"
BOT_NAME = "ЛУЧШИЙ БОТ ПО СТОКАМ"
PREDICT_URL = "https://www.game.guide/grow-a-garden-2-stock-predictor"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class SupportStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()

class SponsorStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_link = State()

LANGUAGES = {
    'ru': {'name': 'Русский', 'flag': '🇷🇺'},
    'en': {'name': 'English', 'flag': '🇬🇧'},
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'it': {'name': 'Italiano', 'flag': '🇮🇹'},
    'de': {'name': 'Deutsch', 'flag': '🇩🇪'},
    'es': {'name': 'Español', 'flag': '🇪🇸'},
    'pt': {'name': 'Português', 'flag': '🇵🇹'},
    'tr': {'name': 'Türkçe', 'flag': '🇹🇷'},
    'ar': {'name': 'العربية', 'flag': '🇸🇦'},
    'zh': {'name': '中文', 'flag': '🇨🇳'},
    'ja': {'name': '日本語', 'flag': '🇯🇵'},
    'ko': {'name': '한국어', 'flag': '🇰🇷'},
}

stock_cache: Dict[str, Dict] = {
    "seeds": {"items": [], "last_update": None},
    "gear": {"items": [], "last_update": None},
    "crates": {"items": [], "last_update": None},
}
item_database: Dict = {}
previous_stock: Dict[str, List[str]] = {}
last_restock_time: Optional[datetime] = None
next_restock_time: Optional[datetime] = None
restock_notified: bool = False

support_messages: Dict[int, Dict] = {}

weather_cache: Dict = {}
previous_weather: Optional[str] = None

predict_cache: Dict = {
    "seeds": [],
    "gear": [],
    "crates": [],
    "next_restock": None,
    "last_update": None,
    "raw_weather": [],
    "raw_now": None,
    "upcoming_seeds": [],
    "upcoming_gears": [],
    "upcoming_crates": []
}
active_stock_displays: Dict[int, int] = {}

def get_stock_countdown_str() -> str:
    if not last_restock_time:
        return "таймер запускается..."

    now = datetime.now(timezone.utc)
    target = last_restock_time + timedelta(seconds=RESTOCK_INTERVAL)
    rem = int((target - now).total_seconds())

    if rem <= 0:
        return "обновление стока..."

    m = rem // 60
    s = rem % 60
    return f"{m}м {s}с"

def generate_stock_text(lang: str) -> str:
    text = get_t(lang, "stock_header")

    seeds = get_items_for_display("seeds", lang)
    text += create_category_header("Seeds", "🌱", len(seeds))
    if not seeds:
        text += get_t(lang, "stock_no_items")
    else:
        for item in seeds:
            text += create_item_line(item, lang)
    text += create_category_footer()

    gear = get_items_for_display("gear", lang)
    text += create_category_header("Gears", "🛠️", len(gear))
    if not gear:
        text += get_t(lang, "stock_no_items")
    else:
        for item in gear:
            text += create_item_line(item, lang)
    text += create_category_footer()

    crates = get_items_for_display("crates", lang)
    text += create_category_header("Crates", "📦", len(crates))
    if not crates:
        text += get_t(lang, "stock_no_items")
    else:
        for item in crates:
            text += create_item_line(item, lang)
    text += create_category_footer()

    if next_restock_time:
        countdown = get_stock_countdown_str()
        time_str = format_restock_time(next_restock_time)
        text += get_t(lang, "stock_countdown", time=time_str, countdown=countdown)

    return text

def clear_active_stock(user_id: int):
    active_stock_displays.pop(user_id, None)

FALLBACK_PRICES = {

    "carrot": "1",
    "strawberry": "10",
    "blueberry": "25",
    "tulip": "40",
    "tomato": "200",
    "apple": "400",
    "bamboo": "700",
    "corn": "2500",
    "cactus": "5000",
    "pineapple": "30000",
    "mushroom": "15000",
    "green_bean": "20000",
    "banana": "30000",
    "grape": "50000",
    "coconut": "140000",
    "mango": "300000",
    "dragon_fruit": "120000",
    "acorn": "700000",
    "cherry": "1200000",
    "sunflower": "5000000",
    "venus_fly_trap": "7000000",
    "pomegranate": "12000000",
    "poison_apple": "25000000",
    "moon_bloom": "65000000",
    "dragons_breath": "90000000",


    "ladder_crate": "30000",
    "bench_crate": "60000",
    "light_crate": "90000",
    "sign_crate": "150000",
    "arch_crate": "200000",
    "roleplay_crate": "300000",
    "bridge_crate": "700000",
    "conveyor_crate": "700000",
    "spring_crate": "900000",
    "seesaw_crate": "1500000",
    "owner_door_crate": "1500000",
    "bear_trap_crate": "TBA",
    "fence_crate": "7000000",
    "teleporter_pad_crate": "20000000",


    "common_sprinkler": "3000",
    "common_watering_can": "2000",
    "sign": "4000",
    "uncommon_sprinkler": "10000",
    "rare_sprinkler": "80000",
    "trowel": "1000",
    "jump_mushroom": "1800",
    "speed_mushroom": "1500",
    "lantern": "12000",
    "megaphone": "4000",
    "shrink_mushroom": "10000",
    "supersize_mushroom": "4500",
    "gnome": "100000",
    "flashbang": "20000",
    "basic_pot": "300000",
    "legendary_sprinkler": "1200000",
    "teleporter": "60000",
    "invisibility_mushroom": "30000",
    "wheelbarrow": "500000",
    "player_magnet": "7000000",
    "strawberry_sniper": "13000000",
    "super_watering_can": "1000000",
    "super_sprinkler": "3000000",
    "grappling_hook": "10000000"
}

FALLBACK_RARITIES = {

    "carrot": "common",
    "strawberry": "common",
    "blueberry": "common",
    "tulip": "uncommon",
    "tomato": "uncommon",
    "apple": "uncommon",
    "bamboo": "rare",
    "corn": "rare",
    "cactus": "rare",
    "pineapple": "rare",
    "mushroom": "epic",
    "green_bean": "epic",
    "banana": "epic",
    "grape": "epic",
    "coconut": "epic",
    "mango": "epic",
    "dragon_fruit": "legendary",
    "acorn": "legendary",
    "cherry": "legendary",
    "sunflower": "legendary",
    "venus_fly_trap": "mythic",
    "pomegranate": "mythic",
    "poison_apple": "mythic",
    "moon_bloom": "super",
    "dragons_breath": "super",
    "dragon_s_breath": "super",
    "baby_cactus": "rare",
    "beanstalk": "secret",
    "briar_rose": "mythic",
    "ghost_pepper": "mythic",
    "glow_mushroom": "epic",
    "horned_melon": "rare",
    "hypno_bloom": "super",
    "poison_ivy": "legendary",
    "romanesco": "mythic",
    "venom_spitter": "mythic",


    "common_watering_can": "common",
    "common_sprinkler": "common",
    "trowel": "common",
    "speed_mushroom": "common",
    "sign": "uncommon",
    "uncommon_sprinkler": "uncommon",
    "rare_sprinkler": "rare",
    "lantern": "rare",
    "jump_mushroom": "rare",
    "shrink_mushroom": "rare",
    "supersize_mushroom": "rare",
    "flashbang": "epic",
    "basic_pot": "epic",
    "megaphone": "epic",
    "invisibility_mushroom": "epic",
    "teleporter": "epic",
    "wheelbarrow": "epic",
    "gnome": "legendary",
    "legendary_sprinkler": "legendary",
    "super_watering_can": "legendary",
    "player_magnet": "legendary",
    "grappling_hook": "mythic",
    "super_sprinkler": "mythic",
    "strawberry_sniper": "mythic",


    "ladder_crate": "common",
    "bench_crate": "uncommon",
    "light_crate": "uncommon",
    "sign_crate": "uncommon",
    "arch_crate": "rare",
    "roleplay_crate": "rare",
    "bridge_crate": "epic",
    "conveyor_crate": "epic",
    "spring_crate": "epic",
    "seesaw_crate": "epic",
    "owner_door_crate": "legendary",
    "bear_trap_crate": "legendary",
    "fence_crate": "legendary",
    "teleporter_pad_crate": "mythic",
    "common_guild_crate": "common",
    "uncommon_guild_crate": "uncommon",
    "rare_guild_crate": "rare",
    "epic_guild_crate": "epic",
    "legendary_guild_crate": "legendary",
    "mythic_guild_crate": "mythic",
    "super_guild_crate": "super",
}

RARITY_ORDER = [
    'super', 'mythic', 'legendary', 'epic',
    'rare', 'uncommon', 'common'
]

RARITY_EMOJIS = {
    'super': '⭐️',
    'mythic': '🟡',
    'legendary': '🔴',
    'epic': '🟣',
    'rare': '🔵',
    'uncommon': '🟢',
    'common': '⚪️'
}

RARITY_NAMES = {
    'super': 'Супер',
    'mythic': 'Мифический',
    'legendary': 'Легендарный',
    'epic': 'Эпический',
    'rare': 'Редкий',
    'uncommon': 'Необычный',
    'common': 'Обычный'
}

RARITY_EMOJIS_FULL = {
    'super': '🌟',
    'mythic': '💎',
    'legendary': '🔴',
    'epic': '🟣',
    'rare': '🔵',
    'uncommon': '🟢',
    'common': '⚪️'
}

WEATHER_EMOJIS = {
    'rain': '🌧️',
    'lightning': '⚡',
    'thunder': '⛈️',
    'rainbow': '🌈',
    'snowfall': '❄️',
    'starfall': '🌠',
    'blood moon': '🌕',
    'bloodmoon': '🌕',
    'gold moon': '🟡',
    'midas': '🟡',
    'rainbow moon': '🌈',
    'rainbowmoon': '🌈',
    'clear': '☀️',
    'none': '☀️'
}

CATEGORY_EMOJIS = {'seeds': '🌱', 'gear': '🛠️', 'crates': '📦'}
CATEGORY_NAMES = {'seeds': 'Seeds', 'gear': 'Gears', 'crates': 'Crates'}

SEED_EMOJIS = {
    'carrot': '🥕',
    'strawberry': '🍓',
    'blueberry': '🫐',
    'tulip': '🌷',
    'tomato': '🍅',
    'apple': '🍎',
    'bamboo': '🎋',
    'corn': '🌽',
    'cactus': '🌵',
    'pineapple': '🍍',
    'mushroom': '🍄',
    'green bean': '🫘',
    'banana': '🍌',
    'grape': '🍇',
    'coconut': '🥥',
    'mango': '🥭',
    'dragon fruit': '🐉',
    'acorn': '🌰',
    'cherry': '🍒',
    'sunflower': '🌻',
    'venus fly trap': '🪴',
    'pomegranate': '🍎',
    'poison apple': '☠️',
    'venom spitter': '💀',
    'moon bloom': '🌙',
    "dragon's breath": '🔥',
    'pumpkin': '🎃',
    'lotus': '🪷',
    'beanstalk': '🌱',
    'glow mushroom': '🍄',
    'thorn rose': '🌹',
    'poison ivy': '☘️',
    'ghost pepper': '🌶️',
    'baby cactus': '🌵',
    'romanesco': '🥦',
    'horned melon': '🍈',
    'pinetree': '🌲',
}

GEAR_EMOJIS = {
    'trowel': '🔧',
    'shovel': '⛏️',
    'rake': '🧹',
    'watering can': '💧',
    'common sprinkler': '💦',
    'uncommon sprinkler': '💦',
    'rare sprinkler': '💦',
    'legendary sprinkler': '💦',
    'super sprinkler': '💦',
    'common watering can': '💧',
    'super watering can': '💧',
    'gnome': '🧝',
    'lantern': '🏮',
    'sign': '📋',
    'teleporter': '🌀',
    'wheelbarrow': '🛒',
    'rainbow': '🌈',
    'freeze ray': '❄️',
    'flashbang': '💥',
    'door crowbar': '🔓',
    'speed mushroom': '⚡',
    'jump mushroom': '⬆️',
    'shrink mushroom': '⬇️',
    'supersize mushroom': '⬆️',
    'megaphone': '📢',
    'basic pot': '🪴',
    'player magnet': '🧲',
    'strawberry sniper': '🎯',
    'invisibility mushroom': '👻',
}

CRATE_EMOJIS = {
    'fence': '🪵',
    'bridge': '🌉',
    'ladder': '🪜',
    'light': '💡',
    'spring': '🔄',
    'seesaw': '⚖️',
    'conveyor': '⚙️',
    'bear trap': '🐻',
    'owner door': '🚪',
    'roleplay': '🎭',
    'teleporter pad': '🌀',
}

def create_category_header(name: str, emoji: str, count: int) -> str:
    line = "─" * 8
    return f"\n{emoji} {line} {name} {line} {emoji}\n"

def create_category_footer() -> str:
    return "─" * 20 + "\n"

def create_item_line(item: Dict, lang: str) -> str:
    name = item["name"]
    rarity = item["rarity"]
    price = item["price"]
    quantity = item["quantity"]
    emoji = item["emoji"]

    rarity_emoji = get_rarity_emoji(rarity)
    rarity_name = get_rarity_name_t(rarity, lang)

    if not emoji:
        emoji = "🟫"

    extra_info = ""
    if item.get("seed_price") and item.get("crop_price"):
        extra_info += f"      └ 🌱 {format_cost(item['seed_price'])} | 🍎 {format_cost(item['crop_price'])}\n"
    if item.get("stock_range"):
        extra_info += f"      └ 📦 {item['stock_range']}\n"

    return (
        f"   {rarity_emoji} {emoji} <b>{name}</b>\n"
        f"      └ 💰 {format_cost(price)} ×{quantity}\n"
        f"      └ {rarity_name}\n"
        f"{extra_info}"
    )

def format_cost(cost) -> str:
    if cost is None or cost == 'None' or cost == 'TBA':
        return "TBA"
    try:
        if isinstance(cost, str):
            cost = cost.replace(',', '').replace('K', '000').replace('M', '000000')
        c = int(str(cost).replace(',', ''))
        if c >= 1000000:
            return f"{c/1000000:.1f}M"
        elif c >= 1000:
            return f"{c/1000:.1f}K"
        else:
            return str(c)
    except:
        return str(cost)

def get_rarity_emoji(rarity: str) -> str:
    rarity_lower = rarity.lower()
    return RARITY_EMOJIS.get(rarity_lower, '⚪️')

def get_rarity_emoji_full(rarity: str) -> str:
    rarity_lower = rarity.lower()
    return RARITY_EMOJIS_FULL.get(rarity_lower, '⚪️')

def get_rarity_name(rarity: str, lang: str = 'ru') -> str:
    return get_rarity_name_t(rarity, lang)

def get_rarity_index(rarity: str) -> int:
    rarity_lower = rarity.lower()
    try:
        return RARITY_ORDER.index(rarity_lower)
    except ValueError:
        return len(RARITY_ORDER)

def normalize_name(name: str) -> str:
    return name.lower().replace("'", "").replace(" ", "_")

def get_emoji_for_item(name: str, category: str) -> str:
    name_lower = name.lower()

    if category == "seeds":
        for key, emoji in SEED_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "🌱"

    elif category == "gear":
        for key, emoji in GEAR_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "🛠️"

    elif category == "crates":
        for key, emoji in CRATE_EMOJIS.items():
            if key in name_lower or name_lower in key:
                return emoji
        return "📦"

    return "🟫"

def get_weather_emoji(weather_name: str) -> str:
    name_lower = weather_name.lower()
    for key, emoji in WEATHER_EMOJIS.items():
        if key in name_lower or name_lower in key:
            return emoji
    return "🌤️"

def get_moscow_time() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=3)

def format_restock_time(dt: datetime) -> str:
    moscow_time = dt + timedelta(hours=3)
    return moscow_time.strftime("%d.%m в %H:%M")

def format_weather_time(dt: datetime) -> str:
    moscow_time = dt + timedelta(hours=3)
    return moscow_time.strftime("%H:%M")

def get_time_of_day(lang: str = 'ru') -> str:
    now = get_moscow_time()
    hour = now.hour

    if 6 <= hour < 12:
        return get_t(lang, "morning")
    elif 12 <= hour < 18:
        return get_t(lang, "day")
    elif 18 <= hour < 22:
        return get_t(lang, "evening")
    else:
        return get_t(lang, "night")

def get_time_of_day_emoji() -> str:
    now = get_moscow_time()
    hour = now.hour

    if 6 <= hour < 12:
        return "🌅"
    elif 12 <= hour < 18:
        return "☀️"
    elif 18 <= hour < 22:
        return "🌅"
    else:
        return "🌙"

def get_current_moscow_time() -> str:
    now = get_moscow_time()
    return now.strftime("%H:%M:%S")

async def fetch_from_api(endpoint: str) -> Optional[Dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/{endpoint}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success", True):
                        return data
                return None
    except Exception as e:
        logger.error(f"Ошибка API {endpoint}: {e}")
        return None

async def fetch_items_database() -> bool:
    global item_database
    data = await fetch_from_api("api/items")
    if data:
        item_database = data
        logger.info(f"Загружено {len(item_database)} предметов")
        return True
    return False

async def fetch_stock(category: str) -> Optional[Dict]:
    return await fetch_from_api(f"stock?category={category}")

async def fetch_weather() -> Optional[Dict]:
    return await fetch_from_api("weather")




ITEM_ID_TO_NAME = {

    "carrot": "Carrot", "strawberry": "Strawberry", "blueberry": "Blueberry",
    "tulip": "Tulip", "tomato": "Tomato", "apple": "Apple", "bamboo": "Bamboo",
    "corn": "Corn", "cactus": "Cactus", "pineapple": "Pineapple", "mushroom": "Mushroom",
    "green_bean": "Green Bean", "banana": "Banana", "grape": "Grape", "coconut": "Coconut",
    "mango": "Mango", "dragon_fruit": "Dragon Fruit", "acorn": "Acorn", "cherry": "Cherry",
    "sunflower": "Sunflower", "venus_fly_trap": "Venus Fly Trap", "pomegranate": "Pomegranate",
    "poison_apple": "Poison Apple", "moon_bloom": "Moon Bloom", "dragons_breath": "Dragon's Breath",
    "dragon_s_breath": "Dragon's Breath", "beanstalk": "Beanstalk", "briar_rose": "Briar Rose",
    "ghost_pepper": "Ghost Pepper", "glow_mushroom": "Glow Mushroom", "horned_melon": "Horned Melon",
    "hypno_bloom": "Hypno Bloom", "poison_ivy": "Poison Ivy", "romanesco": "Romanesco",
    "venom_spitter": "Venom Spitter", "baby_cactus": "Baby Cactus", "pumpkin": "Pumpkin",
    "lotus": "Lotus", "pinetree": "Pinetree",

    "common_sprinkler": "Common Sprinkler", "common_watering_can": "Common Watering Can",
    "sign": "Sign", "uncommon_sprinkler": "Uncommon Sprinkler", "rare_sprinkler": "Rare Sprinkler",
    "trowel": "Trowel", "jump_mushroom": "Jump Mushroom", "speed_mushroom": "Speed Mushroom",
    "lantern": "Lantern", "megaphone": "Megaphone", "shrink_mushroom": "Shrink Mushroom",
    "supersize_mushroom": "Supersize Mushroom", "gnome": "Gnome", "flashbang": "Flashbang",
    "basic_pot": "Basic Pot", "legendary_sprinkler": "Legendary Sprinkler",
    "teleporter": "Teleporter", "invisibility_mushroom": "Invisibility Mushroom",
    "wheelbarrow": "Wheelbarrow", "player_magnet": "Player Magnet",
    "strawberry_sniper": "Strawberry Sniper", "super_watering_can": "Super Watering Can",
    "super_sprinkler": "Super Sprinkler", "grappling_hook": "Grappling Hook",

    "ladder_crate": "Ladder Crate", "bench_crate": "Bench Crate", "light_crate": "Light Crate",
    "sign_crate": "Sign Crate", "arch_crate": "Arch Crate", "roleplay_crate": "Roleplay Crate",
    "bridge_crate": "Bridge Crate", "conveyor_crate": "Conveyor Crate",
    "spring_crate": "Spring Crate", "seesaw_crate": "Seesaw Crate",
    "owner_door_crate": "Owner Door Crate", "bear_trap_crate": "Bear Trap Crate",
    "fence_crate": "Fence Crate", "teleporter_pad_crate": "Teleporter Pad Crate",
    "common_guild_crate": "Common Guild Crate", "uncommon_guild_crate": "Uncommon Guild Crate",
    "rare_guild_crate": "Rare Guild Crate", "epic_guild_crate": "Epic Guild Crate",
    "legendary_guild_crate": "Legendary Guild Crate", "mythic_guild_crate": "Mythic Guild Crate",
    "super_guild_crate": "Super Guild Crate",
}

def resolve_item_name(raw_id: str, raw_name: str) -> str:
    """Convert item id or raw name to a clean display name."""
    if raw_id and raw_id in ITEM_ID_TO_NAME:
        return ITEM_ID_TO_NAME[raw_id]
    if raw_name:
        return raw_name

    return raw_id.replace("_", " ").title() if raw_id else "Unknown"

def resolve_rarity(key: str, db_item: dict, api_rarity: str) -> str:
    """Resolve rarity with proper priority: DB > FALLBACK_RARITIES > API > common."""
    rarity = db_item.get("rarity") or api_rarity or ""
    if not rarity or rarity.lower() in ("common", ""):
        rarity = FALLBACK_RARITIES.get(key, rarity or "common")
    return rarity.lower()

async def fetch_predict() -> Optional[Dict]:
    """Fetch predictions from game.guide API (new schema: shops.seeds.eachItem[].nextAt)."""
    try:






        now_sec = int(datetime.now(timezone.utc).timestamp())

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.growagarden2stock.com/api/predictions",
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"}
            ) as response:
                if response.status != 200:
                    logger.warning(f"Predictions API вернул {response.status}")
                    return None
                data = await response.json(content_type=None)

        schema_ver = data.get("schemaVersion", 0)
        logger.info(f"Predictions API schemaVersion={schema_ver}")


        def parse_shop_items(shop_key: str, category: str) -> list:
            """Parse eachItem list from data[shops][shop_key] into upcoming groups."""
            shops = data.get("shops", {})
            shop = shops.get(shop_key, {})
            each_item = shop.get("eachItem", [])


            if not each_item:
                each_item = data.get(shop_key, [])

            by_time: dict = {}
            for item in each_item:

                ts = item.get("nextAt") or item.get("timestamp")
                if not ts:
                    continue
                raw_id   = item.get("id", "")
                raw_name = item.get("name", "")
                name = resolve_item_name(raw_id, raw_name)
                key  = normalize_name(raw_id or name)
                db_item  = item_database.get(key, {})
                rarity   = resolve_rarity(key, db_item, item.get("rarity", ""))
                qty      = item.get("quantity") or "?"

                by_time.setdefault(ts, []).append({
                    "name": name,
                    "rarity": rarity,
                    "qty": str(qty),
                })

            upcoming = []
            for ts, items in sorted(by_time.items()):
                upcoming.append({"time": ts, "items": items})
            return upcoming

        def pick_next_entry(upcoming: list, target_ts: int, fallback_now: int):
            """Pick the entry closest to target_ts or the first future one."""

            for e in upcoming:
                if e["time"] == target_ts:
                    return e, target_ts

            for e in upcoming:
                if e["time"] >= fallback_now:
                    return e, e["time"]

            if upcoming:
                return upcoming[-1], upcoming[-1]["time"]
            return None, target_ts

        def build_display_list(entry, category: str) -> list:
            if not entry:
                return []
            result = []
            for item in entry.get("items", []):
                name   = item.get("name", "")
                rarity = item.get("rarity", "common")
                qty    = item.get("qty", "?")
                key    = normalize_name(name)
                db_item = item_database.get(key, {})

                price = db_item.get("shecklePrice") or FALLBACK_PRICES.get(key, "TBA")
                result.append({
                    "name": name,
                    "price": format_cost(price),
                    "quantity": str(qty),
                    "rarity": rarity,
                    "emoji": get_emoji_for_item(name, category),
                })
            return result


        upcoming_seeds  = parse_shop_items("seeds",  "seeds")
        upcoming_gears  = parse_shop_items("gears",  "gear")
        upcoming_crates = parse_shop_items("props",  "crates")


        next_restock_ts = ((now_sec // 300) + 1) * 300
        remaining = next_restock_ts - now_sec
        next_restock_str = f"{remaining // 60}м {remaining % 60}с" if remaining > 0 else "0м 0с"

        seeds_entry,  next_restock_ts = pick_next_entry(upcoming_seeds,  next_restock_ts, now_sec)
        gears_entry,  _               = pick_next_entry(upcoming_gears,  next_restock_ts, now_sec)
        crates_entry, _               = pick_next_entry(upcoming_crates, next_restock_ts, now_sec)


        if seeds_entry:
            rem2 = seeds_entry["time"] - now_sec
            if rem2 > 0:
                next_restock_str = f"{rem2 // 60}м {rem2 % 60}с"

        seeds_list  = build_display_list(seeds_entry,  "seeds")
        gear_list   = build_display_list(gears_entry,  "gear")
        crates_list = build_display_list(crates_entry, "crates")

        seeds_list.sort(key=lambda x: get_rarity_index(x["rarity"]))
        gear_list.sort(key=lambda x: get_rarity_index(x["rarity"]))
        crates_list.sort(key=lambda x: get_rarity_index(x["rarity"]))


        raw_weather = (
            data.get("weathers")
            or data.get("weather", [])
        )
        if isinstance(raw_weather, dict):
            raw_weather = [raw_weather]

        logger.info(
            f"✅ Предикт обновлен: {len(seeds_list)} семян, "
            f"{len(gear_list)} орудий, {len(crates_list)} ящиков, "
            f"{len(upcoming_seeds)} временных слотов seeds"
        )

        return {
            "seeds": seeds_list,
            "gear": gear_list,
            "crates": crates_list,
            "next_restock": next_restock_str,
            "last_update": datetime.now(timezone.utc),
            "raw_weather": raw_weather,
            "raw_now": now_sec,
            "upcoming_seeds": upcoming_seeds,
            "upcoming_gears": upcoming_gears,
            "upcoming_crates": upcoming_crates,
        }

    except Exception as e:
        logger.error(f"Ошибка fetch_predict: {e}", exc_info=True)
    return None

async def update_stock_data():
    global stock_cache, previous_stock, last_restock_time, next_restock_time, restock_notified

    logger.info("🔄 Обновление стоков...")

    if not item_database:
        await fetch_items_database()

    new_legendary_items = []
    new_stock_items = []
    current_all_items = {}

    for category in ["seeds", "gear", "crates"]:
        data = await fetch_stock(category)
        if data:
            items = data.get("items", [])
            in_stock_items = [
                item for item in items
                if item.get("in_stock") == 1 or item.get("in_stock") == True
            ]

            current_all_items[category] = [item.get("item_name", "").lower() for item in in_stock_items]

            for item in in_stock_items:
                name = item.get("item_name", "")
                key = normalize_name(name)
                db_item = item_database.get(key, {})


                rarity = db_item.get("rarity") or item.get("rarity")
                if rarity is None or rarity == "" or rarity.lower() == "common":
                    if key in FALLBACK_RARITIES:
                        rarity = FALLBACK_RARITIES[key]
                    else:
                        rarity = rarity or "common"
                rarity = rarity.lower()


                price_val = db_item.get("shecklePrice") or item.get("price")
                if price_val is None or str(price_val).strip().lower() in ['none', 'tba', '']:
                    if key in FALLBACK_PRICES:
                        price_val = FALLBACK_PRICES[key]
                    else:
                        price_val = "TBA"

                prev_items = previous_stock.get(category, [])
                if name.lower() not in prev_items:
                    item_info = {
                        "name": name,
                        "category": category,
                        "rarity": rarity,
                        "price": price_val,
                        "quantity": item.get("quantity", "?"),
                        "emoji": get_emoji_for_item(name, category),
                        "seed_price": db_item.get("seed_price"),
                        "crop_price": db_item.get("crop_price"),
                        "stock_range": db_item.get("stock")
                    }
                    new_stock_items.append(item_info)
                    if rarity in ['super', 'mythic', 'legendary'] and category != 'crates':
                        new_legendary_items.append(item_info)

            stock_cache[category]["items"] = in_stock_items
            stock_cache[category]["last_update"] = datetime.now(timezone.utc)
            logger.info(f"✅ {category}: {len(in_stock_items)}/{len(items)} в наличии")

    previous_stock = current_all_items

    now = datetime.now(timezone.utc)
    if last_restock_time is None or (now - last_restock_time).total_seconds() > RESTOCK_INTERVAL:
        last_restock_time = now
        next_restock_time = now
        restock_notified = False
        logger.info(f"🔄 Новый ресток в {format_restock_time(next_restock_time)} (МСК)")

    if new_legendary_items:
        await notify_legendary_items(new_legendary_items)

    if new_stock_items:
        await send_personal_notifications(new_stock_items)

    logger.info("✅ Стоки обновлены")

async def update_predict():
    global predict_cache

    if not item_database:
        logger.info("📥 База предметов пуста, загружаем перед предиктом...")
        await fetch_items_database()
    data = await fetch_predict()
    if data:
        predict_cache = data
        logger.info(f"✅ Предикт обновлен: {len(data.get('seeds', []))} семян, "
                    f"{len(data.get('gear', []))} орудий, {len(data.get('crates', []))} ящиков")

async def update_weather():
    global weather_cache, previous_weather

    data = await fetch_weather()
    if not data:
        return

    current = data.get("current", {})
    if not current:
        return

    weather_name = current.get("weather_name", "Clear")

    if weather_name not in ["Clear", "None"] and weather_name != previous_weather:
        previous_weather = weather_name
        weather_cache = current

        await notify_weather_change(current)

    weather_cache = current

async def notify_weather_change(weather: Dict):
    weather_name = weather.get("weather_name", "")
    weather_emoji = get_weather_emoji(weather_name)
    started_at = weather.get("started_at")
    time_of_day = get_time_of_day()

    next_update = "скоро"
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            next_update = format_weather_time(dt + timedelta(minutes=2))
        except:
            pass

    message = (
        f"🌦 ПОГОДА СМЕНИЛАСЬ!\n\n"
        f"{weather_emoji} {weather_name}\n"
        f"🕐 {time_of_day}\n"
        f"⏱️ Обновление: {next_update} (МСК)\n\n"
        f"👀 Включи уведомления в канале!\n\n"
        f"🌾 <a href='{BOT_LINK}'>{BOT_NAME}</a>"
    )

    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        logger.info(f"📤 Отправлена погода: {weather_name}")
    except Exception as e:
        logger.error(f"Ошибка отправки погоды: {e}")

async def send_personal_notifications(new_items: List[Dict]):
    if not new_items:
        return

    data = load_data()
    users = data.get("users", {})

    for user_id, info in users.items():
        tracked_items = info.get("tracked_items", [])
        if not tracked_items:
            continue

        tracked_lower = [x.lower() for x in tracked_items]
        lang = get_user_language(int(user_id))

        user_items = []
        for item in new_items:
            item_name = item["name"].lower()
            if item_name in tracked_lower:
                user_items.append(item)

        if user_items:
            text = get_t(lang, "personal_notify_header")
            for item in user_items:
                rarity_emoji = get_rarity_emoji(item["rarity"])

                price_val = item.get("price")
                key = normalize_name(item["name"])
                if price_val is None or str(price_val).strip().lower() in ['none', 'tba', '']:
                    if key in FALLBACK_PRICES:
                        price_val = FALLBACK_PRICES[key]
                    else:
                        price_val = "TBA"

                price = format_cost(price_val)
                text += f"   {rarity_emoji} {item['emoji']} <b>{item['name']}</b> (💰 {price} ×{item['quantity']})\n"

            text += get_t(lang, "personal_notify_footer")

            try:
                await bot.send_message(chat_id=int(user_id), text=text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Не удалось отправить личное уведомление пользователю {user_id}: {e}")

async def send_to_all_channels(text: str):
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Ошибка отправки в основной канал {CHANNEL_ID}: {e}")

async def send_to_connected_channels(text: str):
    data = load_data()
    channels = data.get("channels", [])
    if not channels:
        return

    channel_names = data.get("channel_names", {})
    active_channels = list(channels)
    changed = False

    for channel_id in channels:
        name_str = channel_names.get(channel_id, channel_id)
        try:
            await bot.send_message(
                chat_id=int(channel_id),
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except TelegramForbiddenError as e:
            logger.warning(f"Бот заблокирован/удален из чата {name_str} ({channel_id}), удаляем: {e}")
            if channel_id in active_channels:
                active_channels.remove(channel_id)
                changed = True
        except TelegramBadRequest as e:
            err_msg = str(e).lower()
            if "chat not found" in err_msg or "not member" in err_msg or "not enough rights" in err_msg:
                logger.warning(f"Удаляем чат {name_str} ({channel_id}) из-за ошибки прав/существования: {e}")
                if channel_id in active_channels:
                    active_channels.remove(channel_id)
                    changed = True
            else:
                logger.error(f"Ошибка запроса при отправке в чат {name_str} ({channel_id}): {e}")
        except Exception as e:
            logger.error(f"Временная ошибка отправки в чат {name_str} ({channel_id}): {e}")

    if changed:
        data["channels"] = active_channels
        save_data(data)

async def notify_legendary_items(items: List[Dict]):
    for item in items:
        rarity = item["rarity"]
        name = item["name"]
        emoji = item["emoji"]
        quantity = item["quantity"]
        price = format_cost(item["price"])

        rarity_lower = rarity.lower()
        if rarity_lower == 'legendary':
            rarity_name_feminine = 'Легендарная'
        elif rarity_lower == 'mythic':
            rarity_name_feminine = 'Мифическая'
        elif rarity_lower == 'super':
            rarity_name_feminine = 'Супер'
        else:
            rarity_name_feminine = rarity.capitalize()

        message = (
            f"📣 | Новая {rarity_name_feminine} в стоке!\n"
            f"{emoji} <b>{name}</b> - 💰 {price} - {quantity} шт.\n\n"
            f"<blockquote>успел забрать ⁉️</blockquote>\n"
            f"⚠️ <a href='{BOT_LINK}'>лучший бот по стокам</a>"
        )

        await send_to_all_channels(message)
        await send_to_connected_channels(message)

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"sponsors": [], "users": {}, "user_languages": {}, "channels": []}
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_language(user_id: int) -> str:
    data = load_data()
    return data.get("user_languages", {}).get(str(user_id), "")

def set_user_language(user_id: int, lang: str):
    data = load_data()
    if "user_languages" not in data:
        data["user_languages"] = {}
    data["user_languages"][str(user_id)] = lang
    save_data(data)

async def check_user_subscription(user_id: int, channel: str) -> bool:
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator', 'restricted']
    except Exception as e:
        err_msg = str(e).lower()
        if "admin" in err_msg or "inaccessible" in err_msg or "privileges" in err_msg:
            logger.warning(f"Бот не является администратором в {channel}, проверка подписки пропущена: {e}")
            return True
        logger.error(f"Ошибка проверки подписки {user_id} в {channel}: {e}")
        return False

async def is_user_subscribed(user_id: int, force_check: bool = False) -> bool:
    if user_id in ADMIN_IDS:
        return True

    data = load_data()
    current_time = datetime.now(timezone.utc).timestamp()

    if "users" not in data:
        data["users"] = {}

    user_cache = data["users"].get(str(user_id), {})
    if not force_check and user_cache:
        last_check = user_cache.get("last_check", 0)
        if current_time - last_check < CHECK_CACHE_TIME:
            return user_cache.get("subscribed", False)

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "first_seen": datetime.now(timezone.utc).isoformat()
        }

    if not await check_user_subscription(user_id, CHANNEL_ID):
        data["users"][str(user_id)]["subscribed"] = False
        data["users"][str(user_id)]["last_check"] = current_time
        save_data(data)
        return False

    for sponsor in data.get("sponsors", []):
        channel = sponsor.get("channel")
        if channel and not await check_user_subscription(user_id, channel):
            data["users"][str(user_id)]["subscribed"] = False
            data["users"][str(user_id)]["last_check"] = current_time
            save_data(data)
            return False

    data["users"][str(user_id)]["subscribed"] = True
    data["users"][str(user_id)]["last_check"] = current_time
    save_data(data)
    return True

def get_main_keyboard(user_id: int, lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_stock"), callback_data="view_stock"),
        InlineKeyboardButton(text=get_t(lang, "btn_predict"), callback_data="view_predict"),
        InlineKeyboardButton(text=get_t(lang, "btn_weather"), callback_data="view_weather")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_autostock"), callback_data="auto_stock"),
        InlineKeyboardButton(text=get_t(lang, "btn_channel"), callback_data="auto_stock_channel")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_support"), callback_data="support"),
        InlineKeyboardButton(text=get_t(lang, "btn_language"), callback_data="change_language")
    )
    if user_id in ADMIN_IDS:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ", callback_data="admin_panel")
        )
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить спонсора", callback_data="admin_add_sponsor"),
        InlineKeyboardButton(text="📋 Список", callback_data="admin_list_sponsors")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data="admin_remove_sponsor"),
        InlineKeyboardButton(text="📊 Пользователи", callback_data="admin_list_users")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh_stock"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_subscribe_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    channel_url = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_subscribe"), url=channel_url)
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_check_sub"), callback_data="check_subscription")
    )
    return builder.as_markup()

def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    langs = list(LANGUAGES.items())
    for i in range(0, len(langs), 3):
        row = []
        for lang_code, lang_info in langs[i:i+3]:
            row.append(InlineKeyboardButton(
                text=f"{lang_info['flag']} {lang_info['name']}",
                callback_data=f"set_lang_{lang_code}"
            ))
        builder.row(*row)
    return builder.as_markup()

def get_auto_stock_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 " + get_t(lang, "status_on"), callback_data="auto_stock_on"),
        InlineKeyboardButton(text="🔕 " + get_t(lang, "status_off"), callback_data="auto_stock_off")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="back_to_main")
    )
    return builder.as_markup()

def get_support_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_write"), callback_data="support_write")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="back_to_main")
    )
    return builder.as_markup()

def get_admin_reply_keyboard(user_id: int, msg_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Ответить", callback_data=f"admin_reply_{user_id}_{msg_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_cancel_{user_id}_{msg_id}")
    )
    return builder.as_markup()

def get_items_for_display(category: str, lang: str = 'ru') -> List[Dict]:
    items = stock_cache.get(category, {}).get("items", [])

    enriched = []
    for item in items:
        name = item.get("item_name", "")
        key = normalize_name(name)
        db_item = item_database.get(key, {})


        rarity = db_item.get("rarity") or item.get("rarity")
        if rarity is None or rarity == "" or rarity.lower() == "common":
            if key in FALLBACK_RARITIES:
                rarity = FALLBACK_RARITIES[key]
            else:
                rarity = rarity or "common"
        rarity = rarity.lower()

        price = db_item.get("shecklePrice") or item.get("price")
        if price is None or str(price).strip().lower() in ['none', 'tba', '']:
            if key in FALLBACK_PRICES:
                price = FALLBACK_PRICES[key]
            else:
                price = "TBA"

        emoji = get_emoji_for_item(name, category)

        enriched.append({
            "name": name,
            "rarity": rarity,
            "price": str(price),
            "quantity": item.get("quantity", "?"),
            "emoji": emoji,
            "seed_price": db_item.get("seed_price"),
            "crop_price": db_item.get("crop_price"),
            "stock_range": db_item.get("stock")
        })

    enriched.sort(key=lambda x: get_rarity_index(x["rarity"]))
    return enriched

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    clear_active_stock(user_id)

    data = load_data()

    if "users" not in data:
        data["users"] = {}
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "first_seen": datetime.now(timezone.utc).isoformat(),
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }
        save_data(data)

    lang = get_user_language(user_id)
    if not lang:
        await message.answer(
            get_t("en", "lang_select"),
            reply_markup=get_language_keyboard(),
            parse_mode="HTML"
        )
        return

    if not await is_user_subscribed(user_id):
        text = get_t(lang, "sub_required", channel=CHANNEL_ID)

        sponsors = data.get("sponsors", [])
        if sponsors:
            text += get_t(lang, "sub_sponsors")
            for sponsor in sponsors:
                channel = sponsor.get("channel", "")
                link = sponsor.get("link", "")
                text += f"• {channel}: {link}\n"

        text += "\n⬇️ После подписки нажми кнопку ниже."

        await message.answer(text, reply_markup=get_subscribe_keyboard(), parse_mode="HTML")
        return

    if not stock_cache["seeds"]["items"]:
        await update_stock_data()

    await message.answer(
        "🌱 <b>Grow a Garden 2 Биржа</b>\n\n"
        "📊 Выберите действие:",
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)
    lang_code = callback.data.replace("set_lang_", "")

    if lang_code in LANGUAGES:
        set_user_language(user_id, lang_code)
        await callback.answer(f"✅ Язык установлен: {LANGUAGES[lang_code]['name']}")

        await callback.message.delete()

        if not await is_user_subscribed(user_id):
            data = load_data()
            text = f"🌱 <b>Grow a Garden 2 Stock Bot</b>\n\n"
            text += f"📢 Для доступа подпишись на канал:\n{CHANNEL_ID}\n\n"

            sponsors = data.get("sponsors", [])
            if sponsors:
                text += "📢 <b>А также на спонсоров:</b>\n"
                for sponsor in sponsors:
                    channel = sponsor.get("channel", "")
                    link = sponsor.get("link", "")
                    text += f"• {channel}: {link}\n"

            text += "\n⬇️ После подписки нажми кнопку ниже."
            await callback.message.answer(text, reply_markup=get_subscribe_keyboard(), parse_mode="HTML")
        else:
            await callback.message.answer(
                "🌱 <b>Grow a Garden 2 Биржа</b>\n\n"
                "📊 Выберите действие:",
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML"
            )

@dp.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if await is_user_subscribed(user_id, force_check=True):
        await callback.message.delete()

        await callback.message.answer(
            get_t(lang, "sub_confirmed"),
            reply_markup=get_main_keyboard(user_id, lang),
            parse_mode="HTML"
        )
        await callback.answer(get_t(lang, "sub_confirmed").replace("<b>", "").replace("</b>", "").split("\n")[0])
    else:
        data = load_data()
        sponsors = data.get("sponsors", [])

        text = get_t(lang, "sub_failed")
        text += f"📢 Основной канал: {CHANNEL_ID}\n"

        if sponsors:
            text += get_t(lang, "sub_sponsors")
            for sponsor in sponsors:
                channel = sponsor.get("channel", "")
                link = sponsor.get("link", "")
                text += f"• {channel}: {link}\n"

        text += get_t(lang, "sub_press_btn")

        await callback.message.edit_text(
            text,
            reply_markup=get_subscribe_keyboard(lang),
            parse_mode="HTML"
        )
        await callback.answer(get_t(lang, "sub_error_alert"), show_alert=True)

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    await callback.message.edit_text(
        get_t(lang, "main_header") + get_t(lang, "select_action"),
        reply_markup=get_main_keyboard(user_id, lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "view_stock")
async def view_stock(callback: CallbackQuery):
    user_id = callback.from_user.id

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    if not stock_cache["seeds"]["items"]:
        await update_stock_data()

    text = generate_stock_text(lang)

    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(user_id, lang),
        parse_mode="HTML"
    )

    active_stock_displays[user_id] = callback.message.message_id

def get_predict_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_seeds"), callback_data="predict_seeds"),
        InlineKeyboardButton(text=get_t(lang, "btn_gears"), callback_data="predict_gears"),
        InlineKeyboardButton(text=get_t(lang, "btn_crates"), callback_data="predict_crates")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_exit"), callback_data="back_to_main")
    )
    return builder.as_markup()

def get_predict_back_keyboard(lang: str = 'ru') -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="view_predict")
    )
    return builder.as_markup()

@dp.callback_query(F.data == "view_predict")
async def view_predict(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    text = get_t(lang, "predict_header")

    await callback.message.edit_text(
        text,
        reply_markup=get_predict_keyboard(lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_seeds")
async def predict_seeds(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    if not predict_cache.get("seeds"):
        await update_predict()

    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())

    upcoming_seeds = predict_cache.get("upcoming_seeds", [])

    def build_section(upcoming_list, category, title, emoji, current_lang):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))

            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'secret']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })

        if not items_list:
            return get_t(current_lang, "predict_no_data")

        months_dict = get_t(current_lang, "months")

        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_dict.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)

        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])

        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"

            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_seeds, "seeds", get_t(lang, "predict_seeds_title"), "🌱", lang)

    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_gears")
async def predict_gears(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    if not predict_cache.get("gear"):
        await update_predict()

    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())

    upcoming_gears = predict_cache.get("upcoming_gears", [])

    def build_section(upcoming_list, category, title, emoji, current_lang):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))

            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'secret'] or name.lower() in ['super watering can', 'super sprinkler']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })

        if not items_list:
            return get_t(current_lang, "predict_no_data")

        months_dict = get_t(current_lang, "months")

        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_dict.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)

        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])

        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"

            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_gears, "gear", get_t(lang, "predict_gears_title"), "🛠️", lang)

    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "predict_crates")
async def predict_crates(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    if not predict_cache.get("crates"):
        await update_predict()

    now_sec = predict_cache.get("raw_now")
    if not now_sec:
        now_sec = int(datetime.now(timezone.utc).timestamp())

    upcoming_crates = predict_cache.get("upcoming_crates", [])

    def build_section(upcoming_list, category, title, emoji, current_lang):
        items_list = []
        for entry in upcoming_list:
            ts = entry.get("time")
            if ts < now_sec:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))

            for item in entry.get("items", []):
                name = item.get("name")
                rarity = item.get("rarity", "Common").lower()
                if rarity in ['super', 'mythic', 'legendary']:
                    items_list.append({
                        "name": name,
                        "dt": dt,
                        "emoji": get_emoji_for_item(name, category),
                        "rarity": rarity
                    })

        if not items_list:
            return get_t(current_lang, "predict_no_data")

        months_dict = get_t(current_lang, "months")

        by_date = {}
        for x in items_list:
            dt = x["dt"]
            date_str = f"{dt.day} {months_dict.get(dt.month, '')}"
            by_date.setdefault(date_str, []).append(x)

        sorted_dates = sorted(by_date.keys(), key=lambda d: by_date[d][0]["dt"])

        sec_text = ""
        is_first = True
        for date_str in sorted_dates:
            if is_first:
                sec_text += f"<blockquote>{emoji} <b>{title}</b>\n{date_str}</blockquote>\n"
                is_first = False
            else:
                sec_text += f"<blockquote>{date_str}</blockquote>\n"

            items = sorted(by_date[date_str], key=lambda x: x["dt"])
            for x in items:
                time_str = f"{x['dt'].hour}:{x['dt'].minute:02d}"
                item_rarity = x.get("rarity", "").lower()
                if item_rarity in ['super', 'mythic', 'secret']:
                    item_text = f"<b><u>{x['emoji']} {x['name']}</u></b>"
                else:
                    item_text = f"{x['emoji']} {x['name']}"
                sec_text += f"<code>{time_str}</code> · {item_text}\n"
            sec_text += "\n"
        return sec_text

    text = build_section(upcoming_crates, "crates", get_t(lang, "predict_crates_title"), "📦", lang)

    await callback.message.edit_text(
        text,
        reply_markup=get_predict_back_keyboard(lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "view_weather")
async def view_weather(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    if not predict_cache.get("raw_weather"):
        await update_predict()

    if not weather_cache:
        await update_weather()

    text = get_t(lang, "weather_header")

    time_of_day = get_time_of_day(lang)
    text += get_t(lang, "time_of_day", time=time_of_day)

    if weather_cache:
        weather_name = weather_cache.get("weather_name", "Clear")
        weather_emoji = get_weather_emoji(weather_name)
        started_at = weather_cache.get("started_at")

        if weather_name not in ["Clear", "None"]:
            text += get_t(lang, "weather_effect", emoji=weather_emoji, effect=weather_name)
            if started_at:
                try:
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    text += get_t(lang, "weather_start", time=format_weather_time(dt))
                except:
                    pass
        else:
            text += get_t(lang, "weather_clear")
    else:
        text += get_t(lang, "weather_no_data")

    text += "─" * 20 + "\n\n"

    raw_weather = predict_cache.get("raw_weather", [])
    raw_now = predict_cache.get("raw_now")

    if raw_weather and isinstance(raw_weather, list) and raw_now:
        text += get_t(lang, "moon_schedule")

        upcoming_count = 0
        for event in raw_weather:
            name = event.get("name", "Clear")
            ts = event.get("timestamp", 0)
            if ts < raw_now:
                continue

            dt_msk = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=3)))
            time_str = dt_msk.strftime('%H:%M:%S')

            rel_sec = ts - raw_now
            if rel_sec > 0:
                rel_str = get_t(lang, "in_mins", m=rel_sec // 60)
            else:
                rel_str = get_t(lang, "active_now")

            moon_emoji = get_weather_emoji(name)

            text += f"  • {time_str} ({rel_str}) — {moon_emoji} <b>{name}</b>\n"
            upcoming_count += 1
            if upcoming_count >= 5:
                break
    else:
        text += get_t(lang, "moon_no_data")

    await callback.message.edit_text(
        text,
        reply_markup=get_main_keyboard(user_id, lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "support")
async def support_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    text = get_t(lang, "support_header")

    await callback.message.edit_text(
        text,
        reply_markup=get_support_keyboard(lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "support_write")
async def support_write(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    await callback.message.edit_text(
        get_t(lang, "support_write_msg"),
        parse_mode="HTML"
    )
    await state.set_state(SupportStates.waiting_for_message)
    await callback.answer()

@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text

    lang = get_user_language(user_id)
    if text == "/cancel":
        await message.answer(
            get_t(lang, "support_cancelled"),
            reply_markup=get_main_keyboard(user_id, lang)
        )
        await state.clear()
        return

    sent = False
    for admin_id in ADMIN_IDS:
        try:
            support_messages[admin_id] = {
                "user_id": user_id,
                "message_id": message.message_id,
                "text": text,
                "date": datetime.now(timezone.utc)
            }

            admin_text = (
                f"📩 Новое сообщение!\n\n"
                f"👤 <a href='tg://user?id={user_id}'>Пользователь</a>\n"
                f"🆔 {user_id}\n"
                f"📝 {text}\n\n"
                f"⏱️ {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
            )

            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=get_admin_reply_keyboard(user_id, message.message_id)
            )
            sent = True
            logger.info(f"📤 Сообщение от {user_id} админу {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка админу {admin_id}: {e}")

    if sent:
        await message.answer(
            get_t(lang, "support_sent"),
            reply_markup=get_main_keyboard(user_id, lang),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            get_t(lang, "support_error"),
            reply_markup=get_main_keyboard(user_id, lang),
            parse_mode="HTML"
        )

    await state.clear()

@dp.callback_query(F.data.startswith("admin_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext):
    admin_id = callback.from_user.id

    if admin_id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    data = callback.data.split("_")
    user_id = int(data[2])
    msg_id = int(data[3])

    await state.update_data(reply_to_user=user_id, reply_to_msg=msg_id)

    await callback.message.answer(
        f"✍️ Ответ пользователю\n\nНапишите текст.\n<i>/cancel - отмена</i>",
        parse_mode="HTML"
    )
    await state.set_state(SupportStates.waiting_for_reply)
    await callback.answer()

@dp.message(SupportStates.waiting_for_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    admin_id = message.from_user.id

    if admin_id not in ADMIN_IDS:
        await message.answer("⛔ Нет прав!")
        await state.clear()
        return

    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return

    data = await state.get_data()
    user_id = data.get("reply_to_user")

    if not user_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return

    try:
        lang = get_user_language(int(user_id))
        await bot.send_message(
            chat_id=user_id,
            text=f"{get_t(lang, 'admin_reply_prefix')}\n\n{message.text}",
            parse_mode="HTML"
        )

        await message.answer(
            f"✅ Отправлено!",
            parse_mode="HTML"
        )

        try:
            await message.delete()
        except:
            pass

        logger.info(f"📤 Админ {admin_id} ответил {user_id}")

    except Exception as e:
        await message.answer(
            f"❌ Ошибка: {e}",
            parse_mode="HTML"
        )

    await state.clear()

@dp.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(callback: CallbackQuery):
    admin_id = callback.from_user.id

    if admin_id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    data = callback.data.split("_")
    user_id = int(data[2])

    await callback.message.edit_text(
        f"❌ Отменено\nПользователь: {user_id}"
    )
    await callback.answer("✅ Отменено")

@dp.callback_query(F.data == "auto_stock")
async def auto_stock_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    text = get_t(lang, "auto_stock_desc")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_seeds"), callback_data="auto_stock_list_seeds"),
        InlineKeyboardButton(text=get_t(lang, "btn_gears"), callback_data="auto_stock_list_gears")
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="back_to_main")
    )

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "change_language")
async def change_language_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)

    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    await callback.message.edit_text(
        get_t(lang, "lang_select"),
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )

@dp.my_chat_member()
async def on_bot_chat_member_update(update: ChatMemberUpdated):
    chat_id = update.chat.id
    chat_type = update.chat.type
    new_status = update.new_chat_member.status


    has_access = False
    if chat_type == 'channel' and new_status in ['administrator', 'creator']:
        has_access = True
    elif chat_type in ['group', 'supergroup'] and new_status in ['administrator', 'creator', 'member']:
        has_access = True

    data = load_data()
    if "channels" not in data:
        data["channels"] = []

    channel_id = str(chat_id)

    if has_access:
        if "channel_names" not in data:
            data["channel_names"] = {}

        chat_title = update.chat.title or "Без названия"
        chat_username = update.chat.username
        chat_desc = f"'{chat_title}'"
        if chat_username:
            chat_desc += f" (@{chat_username})"

        data["channel_names"][channel_id] = chat_desc

        if channel_id not in data["channels"]:
            data["channels"].append(channel_id)
            save_data(data)
            logger.info(f"✅ Бот подключен к {chat_type} {chat_desc} ({channel_id}) (статус: {new_status})")

            try:
                message = (
                    "✅ <b>Бот успешно подключен!</b>\n\n"
                    "📢 Теперь я буду отправлять уведомления о легендарных и редких предметах сюда.\n\n"
                    f"🌾 <a href='{BOT_LINK}'>Grow a Garden 2 Stock Bot</a>"
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить приветствие в {chat_type} {chat_id}: {e}")
    else:
        if "channel_names" in data and channel_id in data["channel_names"]:
            name_str = data["channel_names"].pop(channel_id, channel_id)
        else:
            name_str = channel_id

        if channel_id in data["channels"]:
            data["channels"].remove(channel_id)
            save_data(data)
            logger.info(f"❌ Бот отключен от {chat_type} {name_str} ({channel_id}) (статус: {new_status})")

def get_auto_stock_items_keyboard(user_id: int, category: str, page: int = 0, lang: str = 'ru') -> InlineKeyboardMarkup:
    data = load_data()
    user_cache = data.get("users", {}).get(str(user_id), {})
    tracked_items = user_cache.get("tracked_items", [])
    tracked_lower = [x.lower() for x in tracked_items]

    if category == "seeds":
        items_dict = SEED_EMOJIS
        title_emoji = "🌱"
    else:
        items_dict = GEAR_EMOJIS
        title_emoji = "🛠️"

    builder = InlineKeyboardBuilder()
    sorted_names = sorted(items_dict.keys())

    page_size = 12
    total_pages = (len(sorted_names) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(sorted_names))
    page_items = sorted_names[start_idx:end_idx]

    for name in page_items:
        emoji = items_dict[name]
        is_tracked = name.lower() in tracked_lower
        status_symbol = "✅" if is_tracked else "❌"
        display_name = name.title()
        btn_text = f"{emoji} {display_name} {status_symbol}"
        builder.add(InlineKeyboardButton(text=btn_text, callback_data=f"track_toggle:{name}:{category}:{page}"))

    builder.adjust(2)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=get_t(lang, "btn_prev"), callback_data=f"auto_stock_page:{category}:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=get_t(lang, "btn_next"), callback_data=f"auto_stock_page:{category}:{page+1}"))

    builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="auto_stock"))

    return builder.as_markup()

@dp.callback_query(F.data == "auto_stock_list_seeds")
async def auto_stock_list_seeds(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await callback.message.edit_text(
        get_t(lang, "auto_stock_setup_seeds"),
        reply_markup=get_auto_stock_items_keyboard(user_id, "seeds", 0, lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "auto_stock_list_gears")
async def auto_stock_list_gears(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await callback.message.edit_text(
        get_t(lang, "auto_stock_setup_gears"),
        reply_markup=get_auto_stock_items_keyboard(user_id, "gear", 0, lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("auto_stock_page:"))
async def auto_stock_page_change(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    parts = callback.data.split(":")
    category = parts[1]
    page = int(parts[2])

    text_key = "auto_stock_setup_seeds" if category == "seeds" else "auto_stock_setup_gears"

    await callback.message.edit_text(
        get_t(lang, text_key),
        reply_markup=get_auto_stock_items_keyboard(user_id, category, page, lang),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("track_toggle:"))
async def track_toggle_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    item_name = parts[1]
    category = parts[2]
    page = int(parts[3])

    data = load_data()
    if "users" not in data:
        data["users"] = {}
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {}

    user_cache = data["users"][str(user_id)]
    tracked_items = user_cache.get("tracked_items", [])

    tracked_lower = [x.lower() for x in tracked_items]
    item_lower = item_name.lower()

    lang = get_user_language(user_id)
    if item_lower in tracked_lower:
        tracked_items = [x for x in tracked_items if x.lower() != item_lower]
        status_str = get_t(lang, "status_off")
    else:
        tracked_items.append(item_name)
        status_str = get_t(lang, "status_on")

    data["users"][str(user_id)]["tracked_items"] = tracked_items
    save_data(data)

    await callback.answer(f"🔔 {item_name.title()}: {status_str}")

    await callback.message.edit_reply_markup(
        reply_markup=get_auto_stock_items_keyboard(user_id, category, page, lang)
    )

@dp.callback_query(F.data == "auto_stock_channel")
async def auto_stock_channel_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    clear_active_stock(user_id)

    lang = get_user_language(user_id)
    if not await is_user_subscribed(user_id):
        await callback.answer(get_t(lang, "sub_failed_alert"), show_alert=True)
        return

    text = get_t(lang, "add_channel_desc")

    builder = InlineKeyboardBuilder()
    add_channel_url = f"{BOT_LINK}?startchannel=true"
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_add_channel"), url=add_channel_url)
    )
    builder.row(
        InlineKeyboardButton(text=get_t(lang, "btn_back"), callback_data="back_to_main")
    )

    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    data = load_data()
    users = data.get("users", {})

    if not users:
        text = "📊 Список пользователей пуст."
    else:
        total = len(users)
        text = f"📊 Пользователи бота\n"
        text += "─" * 20 + "\n\n"
        text += f"👥 Всего: {total}\n\n"

        user_list = list(users.items())
        user_list.sort(key=lambda x: x[1].get("first_seen", ""), reverse=True)

        for i, (user_id, info) in enumerate(user_list[:50], 1):
            username = info.get("username", "")
            first_name = info.get("first_name", "")
            last_name = info.get("last_name", "")

            name = first_name
            if last_name:
                name += f" {last_name}"
            if username:
                name += f" (@{username})"

            text += f"{i}. {name}\n"
            text += f"   🆔 {user_id}\n"
            text += f"   📅 {info.get('first_seen', '')[:10]}\n\n"

        if total > 50:
            text += f"... и ещё {total - 50} пользователей"

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ Админ панель\n\nВыберите:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_refresh_stock")
async def admin_refresh_stock(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    await callback.answer("🔄 Обновление...")
    await update_stock_data()
    await update_weather()
    await update_predict()

    text = "✅ Обновлено!\n"
    text += "─" * 12 + "\n\n"

    for category in ["seeds", "gear", "crates"]:
        count = len(stock_cache.get(category, {}).get("items", []))
        text += f"{CATEGORY_EMOJIS.get(category, '📦')} {CATEGORY_NAMES.get(category, category)}: {count}\n"

    if predict_cache.get("seeds"):
        text += f"\n🔮 Предикт: {len(predict_cache.get('seeds', []))} предметов"

    if next_restock_time:
        text += f"\n⏱️ Ресток: {format_restock_time(next_restock_time)} (МСК)"

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_add_sponsor")
async def add_sponsor_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 Добавление спонсора\n\nВведите username канала:\n<i>@sponsor</i>",
        parse_mode="HTML"
    )
    await state.set_state(SponsorStates.waiting_for_channel)
    await callback.answer()

@dp.message(SponsorStates.waiting_for_channel)
async def process_sponsor_channel(message: Message, state: FSMContext):
    await state.update_data(channel=message.text.strip())
    await message.answer(
        "📢 Введите ссылку (/skip - пропустить):",
        parse_mode="HTML"
    )
    await state.set_state(SponsorStates.waiting_for_link)

@dp.message(SponsorStates.waiting_for_link)
async def process_sponsor_link(message: Message, state: FSMContext):
    data = load_data()
    user_data = await state.get_data()
    channel = user_data.get("channel")
    link = message.text.strip()

    if link == "/skip":
        link = channel

    data["sponsors"].append({"channel": channel, "link": link})
    save_data(data)

    await message.answer(
        f"✅ Добавлен!\n\n📢 {channel}\n🔗 {link}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()

@dp.callback_query(F.data == "admin_list_sponsors")
async def list_sponsors(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    data = load_data()
    sponsors = data.get("sponsors", [])

    if not sponsors:
        text = "📋 Список пуст."
    else:
        text = "📋 Список спонсоров:\n\n"
        for i, sponsor in enumerate(sponsors, 1):
            text += f"{i}. {sponsor.get('channel')}\n   🔗 {sponsor.get('link')}\n\n"

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_remove_sponsor")
async def remove_sponsor_start(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    data = load_data()
    sponsors = data.get("sponsors", [])

    if not sponsors:
        await callback.message.edit_text("📋 Список пуст.", reply_markup=get_admin_keyboard())
        return

    builder = InlineKeyboardBuilder()
    for i, sponsor in enumerate(sponsors):
        channel = sponsor.get("channel", f"Спонсор {i+1}")
        builder.row(InlineKeyboardButton(
            text=f"❌ {channel}",
            callback_data=f"remove_sponsor_{i}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel"))

    await callback.message.edit_text(
        "🗑 Выберите спонсора:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("remove_sponsor_"))
async def remove_sponsor_confirm(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    index = int(callback.data.split("_")[2])
    data = load_data()
    sponsors = data.get("sponsors", [])

    if 0 <= index < len(sponsors):
        removed = sponsors.pop(index)
        data["sponsors"] = sponsors
        save_data(data)

        await callback.answer("✅ Удален!", show_alert=True)
        await callback.message.edit_text(
            f"✅ Удален!\n\n📢 {removed.get('channel')}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )

async def stock_countdown_updater():
    while True:
        try:
            if active_stock_displays:
                for user_id, msg_id in list(active_stock_displays.items()):
                    try:
                        lang = get_user_language(user_id)
                        text = generate_stock_text(lang)

                        await bot.edit_message_text(
                            chat_id=user_id,
                            message_id=msg_id,
                            text=text,
                            reply_markup=get_main_keyboard(user_id, lang),
                            parse_mode="HTML"
                        )
                    except TelegramBadRequest as e:
                        err_msg = str(e).lower()
                        if "not modified" in err_msg:
                            pass
                        else:
                            logger.info(f"Убираем {user_id} из обновлений стока: {e}")
                            active_stock_displays.pop(user_id, None)
                    except TelegramForbiddenError:
                        logger.info(f"Бот заблокирован пользователем {user_id}, убираем из обновлений")
                        active_stock_displays.pop(user_id, None)
                    except Exception as e:
                        logger.error(f"Ошибка обновления экрана стоков для {user_id}: {e}")
        except Exception as e:
            logger.error(f"Ошибка в stock_countdown_updater: {e}")

        await asyncio.sleep(5)

async def background_updater():
    while True:
        try:
            await update_stock_data()
            await update_weather()
            await update_predict()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
        await asyncio.sleep(POLL_INTERVAL)

async def main():
    logger.info("🚀 Запуск...")

    try:
        await bot.get_chat(CHANNEL_ID)
        logger.info(f"✅ Канал {CHANNEL_ID} найден")
    except Exception as e:
        logger.error(f"❌ Канал {CHANNEL_ID} не найден! Ошибка: {e}")

    logger.info("📥 Загрузка...")
    await fetch_items_database()
    await update_stock_data()
    await update_weather()
    await update_predict()
    logger.info("✅ Готово")

    asyncio.create_task(background_updater())
    asyncio.create_task(stock_countdown_updater())
    logger.info(f"🔄 Фон (интервал: {POLL_INTERVAL}с)")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
