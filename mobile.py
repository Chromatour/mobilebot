# -*- coding: utf-8 -*-

import logging
import sqlite3

from datetime import date, timedelta, datetime
import config
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
import random
from time import time
from weather import WeatherGod


class TelegramBot:
    def __init__(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - '
                                   '%(message)s', level=logging.INFO)

        updater = Updater(token=config.TOKEN_KB)
        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("kick", self.kick, pass_job_queue=True))
        dispatcher.add_handler(CommandHandler("lupaus", self.lupaus, pass_job_queue=True))
        dispatcher.add_handler(MessageHandler(Filters.command, self.commandsHandler))
        dispatcher.add_handler(MessageHandler(Filters.status_update.pinned_message, self.pinned))

        self.commands = {'wabu': self.wabu,
                         'kiitos': self.kiitos,
                         'sekseli': self.sekseli,
                         'pöytä': self.pöytä,
                         'insv': self.insv,
                         'quoteadd': self.quoteadd,
                         'quote': self.quote,
                         'viisaus': self.viisaus,
                         'saa': self.weather,
                         'sää': self.weather,
                         "kuka": self.kuka

                         }

        self.users = {}  # user_id : unix timestamp

        self.create_tables()

        updater.start_polling()
        updater.idle()

    @staticmethod
    def wabu(bot, update):
        wabu = date(2019, 4, 15)
        tanaan = date.today()
        erotus = wabu - tanaan
        bot.send_message(chat_id=update.message.chat_id,
                         text=f'Wabun alkuun on {erotus.days} päivää', disable_notification=True)

    @staticmethod
    def kiitos(bot, update):
        if update.message.reply_to_message is not None:
            bot.send_message(chat_id=update.message.chat_id, text=f'Kiitos {update.message.reply_to_message.from_user.first_name}!',
                             disable_notifications=True)
        else:
            bot.send_message(chat_id=update.message.chat_id, text='Kiitos Jori!', disable_notification=True)

    @staticmethod
    def sekseli(bot, update):
        text = 'Akseli sekseli guu nu kaijakka niko toivio sitä r elsa'
        bot.send_message(chat_id=update.message.chat_id, text=text, disable_notification=True)

    @staticmethod
    def pöytä(bot, update):
        xd = 'CgADBAADyAQAAgq36FKsK7BL1PNfZQI'
        bot.send_animation(chat_id=update.message.chat_id, animation=xd, disable_notification=True)

    @staticmethod
    def insv(bot, update):
        file_id = "CAADBAADqgADsnJvGjljGk2zOaJJAg"
        bot.send_sticker(chat_id=update.message.chat_id, sticker=file_id, disable_notification=True)

    @staticmethod
    def aikaTarkistus(viesti_aika):
        if datetime.today() - viesti_aika < timedelta(0, 30):
            return True
        else:
            return False

    def cooldownFilter(self, update):

        cooldown = 15

        if not update.message.from_user.id:
            # Some updates are not from any user -- ie when bot is added to a group
            return True

        id = update.message.from_user.id

        if id not in self.users.keys():
            # new user, add id to users
            self.users[id] = time()
            return True

        elif id in self.users.keys():
            # old user
            if time() - self.users[id] < cooldown:
                # caught in spam filter
                return False
            else:
                # passed the spam filter.
                self.users[id] = time()
                return True

    def commandsHandler(self, bot, update):
        if not self.aikaTarkistus(update.message.date):
            return
        if update.message.entities is None:
            return
        commands = self.commandParser(update.message)
        for command in commands:
            if command in self.commands:
                if self.cooldownFilter(update):
                    self.commands[command](bot, update)
            else:
                bot.send_message(chat_id=update.message.chat_id, text="/" + command)

    @staticmethod
    def commandParser(msg):
        commands = list()
        for i in msg.entities:
            if i.type == 'bot_command':
                command = msg.text[i.offset + 1: i.offset + i.length].lower()
                temp = command.split('@')
                commands.append(temp[0])

        is_desk = msg.text.find('pöytä')
        if is_desk != -1:
            commands.append(msg.text[is_desk:is_desk+5])
        return commands

    def pinned(self, bot, update):
        try:
            if update.message.pinned_message:
                if update.message.chat_id == config.MOBILE_ID:
                    sql = "INSERT INTO pinned VALUES (?,?,?)"
                    pinned = (update.message.date.isoformat(), update.message.pinned_message.from_user.username,
                              update.message.pinned_message.text)
                    conn = sqlite3.connect(config.DB_FILE)
                    cur = conn.cursor()
                    cur.execute(sql, pinned)
                    conn.commit()
                    conn.close()

        except KeyError:
            return False

    def quoteadd(self, bot, update):
        text = update.message.text
        first_space = 9
        try:
            second_space = text.find(' ', first_space + 1)
        except IndexError:
            bot.send_message(chat_id=update.message.chat_id, text="Opi käyttämään komentoja pliide bliis!!")
            return

        if second_space != -1:
            quote = (text[10:second_space].lower(), text[second_space + 1:])
            conn = sqlite3.connect(config.DB_FILE)
            cur = conn.cursor()
            sql = "INSERT INTO quotes VALUES (?,?)"
            cur.execute(sql, quote)
            conn.commit()
            conn.close()
            bot.send_message(chat_id=update.message.chat_id, text="Sitaatti suhahti")
        else:
            bot.send_message(chat_id=update.message.chat_id, text="Opi käyttämään komentoja pliide bliis!!")

    def quote(self, bot, update):
        space = update.message.text.find(' ')
        conn = sqlite3.connect(config.DB_FILE)
        c = conn.cursor()
        if space == -1:
            c.execute("SELECT * FROM quotes")
            quotes = c.fetchall()
            i = self.random_select(len(quotes)-1)
        else:
            name = update.message.text[space + 1 :]
            c.execute("SELECT * FROM quotes WHERE name=?", (name.lower(),))
            quotes = c.fetchall()
            if len(quotes) == 0:
                bot.send_message(chat_id=update.message.chat_id, text='Ei löydy')
                return
            i = self.random_select(len(quotes)-1)
        bot.send_message(chat_id=update.message.chat_id, text=f'"{quotes[i][1]}" -{quotes[i][0].capitalize()}')

    def viisaus(self, bot, update):
        conn = sqlite3.connect(config.DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM sananlaskut")
        wisenings = c.fetchall()
        i = self.random_select(len(wisenings)-1)
        bot.send_message(chat_id=update.message.chat_id, text=wisenings[i][0])

    def kuka(self, bot, update):
        question = update.message.text.find(" ")
        if question == -1:
            bot.send_message(chat_id=update.message.chat_id, text="Eipä ollu kysymys...")
            return
        elif update.message.text[-1] != "?":
            bot.send_message(chat_id=update.message.chat_id, text="Kysymysmuotoisen virkkeen tulee päättyä kysymystä ilmaisevaan välimerkkiin.")
            return
        index = random.randint(0, len(config.MEMBERS)-1)
        bot.send_message(chat_id=update.message.chat_id, text=config.MEMBERS[index])

    def lupaus(self, bot, update, job_queue):
        promise = [update.message.chat_id, update.message.message_id, update.message.from_user.username]
        job_queue.run_once(self.muistutus, 86400, context=promise)
        update.message.reply_text("Tää muistetaan!")

    def muistutus(self, bot, job):
        bot.forwardMessage(job.context[0], job.context[0], job.context[1], disable_notification=True)
        bot.send_message(chat_id=job.context[0], text="@"+job.context[2], disable_notifications=True)

    @staticmethod
    def random_select(max):
        rand_int = random.randint(0, max)
        return rand_int

    def create_tables(self):
        conn = sqlite3.connect(config.DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS pinned (date text, name text, text text)''')
        c.execute('''CREATE TABLE IF NOT EXISTS quotes (name text, quote text unique)''')
        c.execute('''CREATE TABLE IF NOT EXISTS sananlaskut (teksti text)''')
        c.execute('''CREATE TABLE IF NOT EXISTS adjektiivit (adj text)''')
        c.execute('''CREATE TABLE IF NOT EXISTS substantiivit (sub text)''')
        conn.close()

    def weather(self, bot, update):

        try:
            city = update.message.text[5:]
            weather = WeatherGod()
            bot.send_message(chat_id=update.message.chat_id,
                             text=weather.generateWeatherReport(city))
        except AttributeError:
            bot.send_message(chat_id=update.message.chat_id,
                             text="Komento vaatii parametrin >KAUPUNKI< \n"
                                  "Esim: /saa Hervanta ")
            return

    def kick(self, bot, update,job_queue):
        try:
            bot.kickChatMember(update.message.chat.id, update.message.from_user.id)
            job_queue.run_once(self.invite, 60, context=[update.message.chat_id, update.message.from_user.id])
        except:
            bot.send_message(chat_id=update.message.chat_id, text="Vielä joku päivä...")

    def invite(self, bot, job):
        bot.unBanChatMember(chat_id=job.context[0], user_id=job.context[1])
'''
    def juoma(self, bot, update):

        juomat = ('olutta',
                  'Jaloviinaa*',
                  'Jaloviinaa**',
                  'Jaloviinaa***',
                  'Vergiä',
                  'vodkaa',
                  'kiljua',
                  'glögiä',
                  'vettä',
                  'Coca-Colaa',
                  'tequilaa',
                  'energiajuomaa',
                  'lonkeroa',
                  'giniä',
                  'Spriteä',
                  'Gambinaa',
                  'maitoa',
                  'kahvia',
                  'kuohuviiniä',
                  'shamppanjaa',
                  'pontikkaa',
                  'simaa',
                  'sangriaa',
                  'martinia',
                  'Bacardia',
                  'tonic-vettä',
                  'siideriä',
                  'absinttia',
                  'punaviiniä',
                  'valkoviiniä',
                  'roséviiniä',
                  'bensaa',
                  )

        resepti = ""
        for i in range(1):
            tilavuus = random.randrange(5, 45, 5)
            resepti += tilavuus + " cl " + random.choice(juomat)

        resepti += "."


    def (self, bot, update):
        choices = {1:'Jallu', 2:'Kalja', 3:'Lonkero'}
        text = update.message.text
'''

if __name__ == '__main__':
    TelegramBot()
