###
# Copyright (c) 2004-2005, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

nonAlphaNumeric = filter(lambda s: not s.isalnum(), utils.str.chars)

WordDict = utils.InsensitivePreservingDict

class WordStatsDB(plugins.ChannelUserDB):
    def __init__(self, *args, **kwargs):
        self.channelWords = ircutils.IrcDict()
        plugins.ChannelUserDB.__init__(self, *args, **kwargs)

    def close(self):
        if self.channelWords:
            plugins.ChannelUserDB.close(self)

    def serialize(self, v):
        L = []
        for (word, count) in v.iteritems():
            L.append('%s:%s' % (word, count))
        return L

    def deserialize(self, channel, id, L):
        d = WordDict()
        for s in L:
            (word, count) = s.split(':')
            count = int(count)
            d[word] = count
            if channel not in self.channelWords:
                self.channelWords[channel] = WordDict()
            self.channelWords[channel].setdefault(word, 0)
            self.channelWords[channel][word] += count
        return d

    def getWordCount(self, channel, id, word):
        return self[channel, id][word]

    def getUserWordCounts(self, channel, id):
        return self[channel, id].items()

    def getWords(self, channel):
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        L = self.channelWords[channel].keys()
        L.sort()
        return L

    def getTotalWordCount(self, channel, word):
        return self.channelWords[channel][word]

    def getNumUsers(self, channel):
        i = 0
        for ((chan, _), _) in self.iteritems():
            if ircutils.nickEqual(chan, channel):
                i += 1
        return i

    def getTopUsers(self, channel, word, n):
        L = [(id, d[word]) for ((chan, id), d) in self.iteritems()
             if ircutils.nickEqual(channel, chan) and word in d]
        utils.sortBy(lambda (_, i): i, L)
        L = L[-n:]
        L.reverse()
        return L

    def getRankAndNumber(self, channel, id, word):
        L = self.getTopUsers(channel, word, 0)
        n = 0
        for (someId, count) in L:
            n += 1
            if id == someId:
                return (n, count)
        raise KeyError

    def addWord(self, channel, word):
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        self.channelWords[channel][word] = 0
        for ((chan, id), d) in self.iteritems():
            if ircutils.nickEqual(chan, channel):
                if word not in d:
                    d[word] = 0

    def delWord(self, channel, word):
        if word in self.channelWords[channel]:
            del self.channelWords[channel][word]
        for ((chan, id), d) in self.iteritems():
            if ircutils.nickEqual(chan, channel):
                if word in d:
                    del d[word]

    def addMsg(self, msg):
        assert msg.command == 'PRIVMSG'
        (channel, text) = msg.args
        if not ircutils.isChannel(channel):
            return
        channel = plugins.getChannel(channel)
        text = text.strip().lower()
        if not text:
            return
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            return
        msgwords = [s.strip(nonAlphaNumeric).lower() for s in text.split()]
        if channel not in self.channelWords:
            self.channelWords[channel] = {}
        for word in self.channelWords[channel]:
            lword = word.lower()
            count = msgwords.count(lword)
            if count:
                self.channelWords[channel][word] += count
                if (channel, id) not in self:
                    self[channel, id] = {}
                if word not in self[channel, id]:
                    self[channel, id][word] = 0
                self[channel, id][word] += count


filename = conf.supybot.directories.data.dirize('WordStats.db')

class WordStats(callbacks.Plugin):
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(WordStats, self)
        self.__parent.__init__(irc)
        self.db = WordStatsDB(filename)
        self.queried = False
        self._flush = self.db.flush
        world.flushers.append(self._flush)

    def die(self):
        world.flushers.remove(self._flush)
        self.db.close()
        self.__parent.die()

    def callCommand(self, *args, **kwargs):
        self.queried = True
        return self.__parent.callCommand(*args, **kwargs)

    def doPrivmsg(self, irc, msg):
        # This depends on the fact that it's called after the command.
        try:
            channel = msg.args[0]
            if irc.isChannel(channel):
                if not (self.queried and
                        self.registryValue('ignoreQueries', channel)):
                    self.db.addMsg(msg)
                else:
                    self.log.debug('Queried and ignoring.')
        finally:
            self.queried = False

    def add(self, irc, msg, args, channel, word):
        """[<channel>] <word>

        Keeps stats on <word> in <channel>.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        word = word.strip()
        if word.strip(nonAlphaNumeric) != word:
            irc.error('<word> must not contain non-alphanumeric chars.')
            return
        self.db.addWord(channel, word)
        irc.replySuccess()
    add = wrap(add, ['channeldb', 'somethingWithoutSpaces'])

    def remove(self, irc, msg, args, channel, word):
        """[<channel>] <word>

        Removes <word> from the list of words being tracked.  If <channel> is
        not specified, uses current channel.
        """
        words = self.db.getWords(channel)
        if words:
            if word in words:
                self.db.delWord(channel, word)
                irc.replySuccess()
            else:
                irc.error(format('%q doesn\'t look like a word I am keeping '
                                 'stats on.' % word))
        else:
            irc.error('I am not currently keeping any word stats.')
    remove = wrap(remove, ['channeldb', 'somethingWithoutSpaces'])

    def wordstats(self, irc, msg, args, channel, user, word):
        """[<channel>] [<user>] [<word>]

        With no arguments, returns the list of words that are being monitored
        for stats.  With <user> alone, returns all the stats for that user.
        With <word> alone, returns the top users for that word.  With <user>
        and <word>, returns that user's stat for that word. <channel> is only
        needed if not said in the channel.  (Note: if only one of <user> or
        <word> is given, <word> is assumed first and only if no stats are
        available for that word, do we assume it's <user>.)
        """
        if not user and not word:
            words = self.db.getWords(channel)
            if words:
                s = format('I am currently keeping stats for %L.', words)
                irc.reply(s)
            else:
                irc.reply('I am not currently keeping any word stats.')
                return
        elif user and word:
            try:
                count = self.db.getWordCount(channel, user.id, word)
            except KeyError:
                irc.error(format('I\'m not keeping stats on %s.', word))
                return
            if count:
                s = format('%s has said %q %n.',
                           user.name, word, (count, 'time'))
                irc.reply(s)
            else:
                irc.error(format('%s has never said %q.', user, word))
        elif word in WordDict.fromkeys(self.db.getWords(channel)):
            total = self.db.getTotalWordCount(channel, word)
            if total == 0:
                irc.reply(format('I\'m keeping stats on %s, but I haven\'t '
                                 'seen it in this channel.', word))
                return
            n = self.registryValue('rankingDisplay', channel)
            try:
                id = ircdb.users.getUserId(msg.prefix)
                (rank, number) = self.db.getRankAndNumber(channel, id, word)
            except (KeyError, ValueError):
                id = None
                rank = None
                number = None
            ers = format('%qer', word)
            L = []
            for (userid, count) in self.db.getTopUsers(channel, word, n):
                if userid == id:
                    rank = None
                try:
                    username = ircdb.users.getUser(userid).name
                    L.append(format('%s: %i', username, count))
                except KeyError:
                    L.append(format('%s: %i', 'unregistered user', count))
            ret = format('Top %n (out of a total of %n seen):',
                         (len(L), ers), (total, format('%q', word)))
            users = self.db.getNumUsers(channel)
            if rank is not None:
                s = format('  You are ranked %i out of %n with %n.',
                           rank, (users, ers), (number, format('%q', word)))
            else:
                s = ''
            ret = format('%s %L.%s', ret, L, s)
            irc.reply(ret)
        elif word:
            irc.error(format('%q doesn\'t look like a word I\'m keeping '
                             'stats on or a user in my database.', word))
        else:
            try:
                L = [format('%q: %i', w, c)
                     for (w, c) in self.db.getUserWordCounts(channel,user.id)]
                L.sort()
                irc.reply(format('%L', L))
            except KeyError:
                irc.error(format('I have no wordstats for %s.', user.name))
    wordstats = wrap(wordstats,
                     ['channeldb',
                      optional('otherUser'),
                      additional('lowered')])

Class = WordStats


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
