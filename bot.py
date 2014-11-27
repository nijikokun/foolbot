#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Foolish bot to look up phrases, send the user a reply, and add them to a list
'''

import os
import re
import time
import random
import logging
import logging.handlers
import tweepy
import tweebot as twb

from subprocess import call
from config import config
from queries import queries
from phrases import phrases

def initRepository():
    if config['repo'] is not '':
        if os.path.exists('repo/'):
            call('cd repo/; git pull origin master', shell=True)
        else:
            call(['git', 'clone', str(config['repo']), 'repo'])

def UnblockUsers(api):
    if config['repo'] is not '':
        with open('repo/whitelist.txt', 'r') as file:
            users = list(file)

            for user in users:
                api.destroy_block(screen_name=user)
                logging.info('unblocking @%s', user)

def BlockedFilter(context, entity):
    settings = context.settings
    user_id = entity.author.id
    reply_to = entity.author.screen_name
    if reply_to == settings.get('username'):
        return False
    if user_id in context.history:
        return False
    if config['repo'] is not '':
        with open('repo/whitelist.txt', 'r') as file:
            if reply_to in list(file):
                return False
    return True

class FoolishReplyClass(twb.ReplyTemplate):
    def validate_templates(cls, templates):
        return templates

    '''Chooses template and appends link to repository'''
    def render_template(self, context, entity):
        return random.choice(self.templates).format(twb._author(entity), 'http://blocktogether.com/' + config['link'])

    '''Sends direct message generated from template'''
    def reply(self, context, entity):
        reply_id   = entity.id
        user_id    = entity.author.id
        user_name  = entity.author.screen_name
        text       = self.render_template(context, entity)

        # Block the user
        logging.info('Blocking: %s | %s' % (user_id, user_name))
        context.api.create_block(id=user_id)

        # Reply to the user
        if config['reply']:
            context.api.update_status(text, reply_id)
            logging.info('Replying to tweet %s with %s' % (reply_id, text))

    def __call__(self, context, entity):
        try:
            result = self.reply(context, entity)
            context.history.append(entity.author.id)
            return result
        except tweepy.error.TweepError, e:
            logging.error('%s | %s' % (entity.author.id, str(e)))
            return False

def main():
    initRepository()

    # Setup Queries
    for index, value in enumerate(queries):
        queries[index] = twb.SearchQuery(value)

    # Setup Bot
    bot = twb.Context({
        'app_name'        : config['app_name'],
        'username'        : config['username'],
        'consumer_key'    : config['consumer_key'],
        'consumer_secret' : config['consumer_secret'],
        'access_key'      : config['access_key'],
        'access_secret'   : config['access_secret'],
        'timeout'         : config['timeout'] or 1 * 60, # once every minute.
        'history_file'    : config['history_file'] or 'history.json',
    })

    twb.enable_logging(bot)
    UnblockUsers(bot.get_api())

    bot.start_forever(
        twb.MultiPart.Add(*queries),
        twb.MultiPart.And(BlockedFilter),
        FoolishReplyClass(phrases))

if __name__ == '__main__':
    main()
