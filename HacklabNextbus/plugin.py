###
# Copyright (c) 2009, Paul V
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import re
 
class HacklabNextbus(callbacks.Plugin):
    """Add the help for "@plugin help HacklabNextbus" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _get_eta(self, url):
        regex = 'span style="font-size: \d+px; font-weight: bold;">&nbsp;(\d+|Arriving)'
	minutes = []
        page = utils.web.getUrl(url)
        for match in re.finditer(regex, page): 
            minutes.append(match.group(1))
        return minutes

    def nextbus(self, irc, msg, args):
        """

        Gets the ETA of the next 510 streetcar
        """

        north_url = "http://www.nextbus.com/wireless/miniPrediction.shtml?a=ttc&r=510&d=510_northbound&s=spadnass_n"
        south_url = "http://www.nextbus.com/wireless/miniPrediction.shtml?a=ttc&r=510&d=510_southbound&s=spadnass_s"

        irc.reply("(510 @ Nassau) Northbound: %s minutes, Southbound: %s minutes" % (','.join(self._get_eta(north_url)), 
','.join(self._get_eta(south_url))))
    nextbus = wrap(nextbus)


Class = HacklabNextbus


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
