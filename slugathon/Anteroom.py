#!/usr/bin/env python2.3

try:
    import pygtk
    pygtk.require('2.0')
except (ImportError, AttributeError):
    pass
import gtk
from gtk import glade
import sys
import time
import sets
from twisted.internet import reactor
import NewGame
import WaitingForPlayers


class Anteroom:
    """GUI for a multiplayer chat and game finding lobby."""
    def __init__(self, user):
        self.user = user
        self.glade = glade.XML('../glade/anteroom.glade')
        self.widgets = ['anteroomWindow', 'chatEntry', 'chatView', 'gameList',
          'userList', 'newGameButton']
        for widgetName in self.widgets:
            setattr(self, widgetName, self.glade.get_widget(widgetName))
        self.usernames = sets.Set()
        self.games = []
        self.anteroomWindow.connect("destroy", quit)

        self.chatEntry.connect("key-press-event", self.cb_keypress)
        self.newGameButton.connect("button-press-event", self.cb_click)

        pixbuf = gtk.gdk.pixbuf_new_from_file(
          '../images/creature/Colossus.gif')
        self.anteroomWindow.set_icon(pixbuf)
        def1 = user.callRemote("getUserNames")
        def1.addCallbacks(self.gotUserNames, self.failure)

    def gotUserNames(self, usernames):
        self.usernames = sets.Set(usernames)
        print "Anteroom got usernames", usernames
        def1 = self.user.callRemote("getGames")
        def1.addCallbacks(self.gotGames, self.failure)

    def gotGames(self, games):
        print "Anteroom got games", games
        self.games = games

        self.userStore = gtk.ListStore(str)
        self.updateUserStore()
        self.userList.set_model(self.userStore)
        selection = self.userList.get_selection()
        selection.set_select_function(self.cb_userList_select, None)
        column = gtk.TreeViewColumn('User Name', gtk.CellRendererText(),
          text=0)
        self.userList.append_column(column)

        self.gameStore = gtk.ListStore(str, str, str, str, int, int)
        self.updateGameStore()
        self.gameList.set_model(self.gameStore)
        selection = self.gameList.get_selection()
        selection.set_select_function(self.cb_gameList_select, None)
        headers = ['Game Name', 'Creator', 'Create Time', 'Start Time',
          'Min Players', 'Max Players']
        for (ii, title) in enumerate(headers):
            column = gtk.TreeViewColumn(title, gtk.CellRendererText(),
              text=ii)
            self.gameList.append_column(column)
        self.anteroomWindow.show_all()

    def updateUserStore(self):
        sorted_usernames = list(self.usernames)
        sorted_usernames.sort()
        leng = len(self.userStore)
        for ii, username in enumerate(sorted_usernames):
            if ii < leng:
                self.userStore[ii, 0] = (username,)
            else:
                self.userStore.append((username,))
        leng = len(sorted_usernames)
        while len(self.userStore) > leng:
            del self.userStore[leng]

    def gamedict_to_tuple(self, gamedict):
        d = gamedict
        return (d["name"], d["creator"], time.ctime(d["create_time"]), 
          time.ctime(d["start_time"]), d["min_players"], d["max_players"])

    def updateGameStore(self):
        leng = len(self.gameStore)
        for ii, game in enumerate(self.games):
            gametuple = self.gamedict_to_tuple(game)
            if ii < leng:
                self.gameStore[ii, 0] = gametuple
            else:
                self.gameStore.append(gametuple)
        leng = len(self.games)
        while len(self.gameStore) > leng:
            del self.gameStore[leng]

    def failure(self, error):
        print "Anteroom.failure", self, error
        reactor.stop()

    def addUsername(self, username):
        self.usernames.add(username)
        self.updateUserStore()

    def delUsername(self, username):
        self.usernames.remove(username)
        self.updateUserStore()

    def cb_insert_text(self, *args):
        print "cb_insert_text", args

    def cb_keypress(self, entry, event):
        ENTER_KEY = 65293  # XXX Find a cleaner way to do this.
        if event.keyval == ENTER_KEY:
            text = self.chatEntry.get_text()
            if text:
                def1 = self.user.callRemote("send_chat_message", text)
                def1.addErrback(self.failure)
                self.chatEntry.set_text("")

    def cb_click(self, widget, event):
        print "clicked new game button"
        newgame = NewGame.NewGame(self.user)
        wfp = WaitingForPlayers.WaitingForPlayers(self.user, newgame.name,
          newgame.min_players, newgame.max_players)

    def receive_chat_message(self, message):
        buffer = self.chatView.get_buffer()
        message = message.strip() + "\n"
        it = buffer.get_end_iter()
        buffer.insert(it, message)
        self.chatView.scroll_to_mark(buffer.get_insert(), 0)

    def add_game(self, gamedict):
        self.games.append(gamedict)
        self.updateGameStore()

    def cb_userList_select(self, path, unused):
        index = path[0]
        print "userList_select", index
        row = self.userStore[index, 0]
        name = row[0]
        print "name is", name
        return False

    def cb_gameList_select(self, path, unused):
        index = path[0]
        print "gameList_select", index
        game = self.games[index]
        print "game is", game
        # TODO menu with join option -> WaitingForPlayers
        return False

def quit(unused):
    sys.exit()

