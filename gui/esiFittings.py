import json

import requests
# noinspection PyPackageRequirements
import wx
from logbook import Logger

import gui.globalEvents as GE
from eos.db import getItem
from eos.saveddata.cargo import Cargo
from gui.auxFrame import AuxiliaryFrame
from gui.display import Display
from service.esi import Esi
from service.esiAccess import APIException
from service.fit import Fit
from service.port import Port
from service.port.esi import ESIExportException


pyfalog = Logger(__name__)


class EveFittings(AuxiliaryFrame):

    def __init__(self, parent):
        super().__init__(
            parent, id=wx.ID_ANY, title="Browse EVE Fittings", pos=wx.DefaultPosition,
            size=wx.Size(750, 450), resizeable=True)

        self.mainFrame = parent
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        characterSelectSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.charChoice = wx.Choice(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [])
        characterSelectSizer.Add(self.charChoice, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.updateCharList()

        self.fetchBtn = wx.Button(self, wx.ID_ANY, "Fetch Fits", wx.DefaultPosition, wx.DefaultSize, 5)
        characterSelectSizer.Add(self.fetchBtn, 0, wx.ALL, 5)
        mainSizer.Add(characterSelectSizer, 0, wx.EXPAND, 5)

        self.sl = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        mainSizer.Add(self.sl, 0, wx.EXPAND | wx.ALL, 5)

        contentSizer = wx.BoxSizer(wx.HORIZONTAL)
        browserSizer = wx.BoxSizer(wx.VERTICAL)

        self.fitTree = FittingsTreeView(self)
        browserSizer.Add(self.fitTree, 1, wx.ALL | wx.EXPAND, 5)
        browserSizer.SetItemMinSize(0, 200, 0)
        contentSizer.Add(browserSizer, 0, wx.EXPAND, 0)
        fitSizer = wx.BoxSizer(wx.VERTICAL)

        self.fitView = FitView(self)
        fitSizer.Add(self.fitView, 1, wx.ALL | wx.EXPAND, 5)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.importBtn = wx.Button(self, wx.ID_ANY, "Import to pyfa", wx.DefaultPosition, wx.DefaultSize, 5)
        self.deleteBtn = wx.Button(self, wx.ID_ANY, "Delete from EVE", wx.DefaultPosition, wx.DefaultSize, 5)
        btnSizer.Add(self.importBtn, 1, wx.ALL, 5)
        btnSizer.Add(self.deleteBtn, 1, wx.ALL, 5)
        fitSizer.Add(btnSizer, 0, wx.EXPAND)

        contentSizer.Add(fitSizer, 1, wx.EXPAND, 0)
        mainSizer.Add(contentSizer, 1, wx.EXPAND, 5)

        self.fetchBtn.Bind(wx.EVT_BUTTON, self.fetchFittings)
        self.importBtn.Bind(wx.EVT_BUTTON, self.importFitting)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.deleteFitting)

        self.Bind(wx.EVT_CHAR_HOOK, self.kbEvent)

        self.statusbar = wx.StatusBar(self)
        self.statusbar.SetFieldsCount()
        self.SetStatusBar(self.statusbar)

        self.SetSizer(mainSizer)
        self.Layout()
        self.SetMinSize(self.GetSize())

        self.Centre(wx.BOTH)

    def updateCharList(self):
        sEsi = Esi.getInstance()
        chars = sEsi.getSsoCharacters()

        self.charChoice.Clear()
        for char in chars:
            self.charChoice.Append(char.characterName, char.ID)
        if len(chars) > 0:
            self.charChoice.SetSelection(0)

    def kbEvent(self, event):
        keycode = event.GetKeyCode()
        mstate = wx.GetMouseState()
        if keycode == wx.WXK_ESCAPE and mstate.GetModifiers() == wx.MOD_NONE:
            self.Close()
            return
        event.Skip()

    def getActiveCharacter(self):
        selection = self.charChoice.GetCurrentSelection()
        return self.charChoice.GetClientData(selection) if selection not in (None, -1) else None

    def fetchFittings(self, event):
        sEsi = Esi.getInstance()
        waitDialog = wx.BusyInfo("Fetching fits, please wait...", parent=self)
        activeChar = self.getActiveCharacter()
        if activeChar is None:
            msg = "Need at least one ESI character to fetch"
            pyfalog.warning(msg)
            self.statusbar.SetStatusText(msg)
            return
        try:
            self.fittings = sEsi.getFittings(activeChar)
            # self.cacheTime = fittings.get('cached_until')
            # self.updateCacheStatus(None)
            # self.cacheTimer.Start(1000)
            self.fitTree.populateSkillTree(self.fittings)
            del waitDialog
        except requests.exceptions.ConnectionError:
            msg = "Connection error, please check your internet connection"
            pyfalog.error(msg)
            self.statusbar.SetStatusText(msg)
        except APIException as ex:
            #  Can't do this in a finally because then it obscures the message dialog
            del waitDialog  # noqa: F821
            ESIExceptionHandler(self, ex)
        except Exception as ex:
            del waitDialog  # noqa: F821
            raise ex

    def importFitting(self, event):
        selection = self.fitView.fitSelection
        if not selection:
            return
        data = self.fitTree.fittingsTreeCtrl.GetItemData(selection)
        sPort = Port.getInstance()
        import_type, fits = sPort.importFitFromBuffer(data)
        self.mainFrame._openAfterImport(fits)

    def deleteFitting(self, event):
        sEsi = Esi.getInstance()
        selection = self.fitView.fitSelection
        if not selection:
            return
        data = json.loads(self.fitTree.fittingsTreeCtrl.GetItemData(selection))

        with wx.MessageDialog(
            self, "Do you really want to delete %s (%s) from EVE?" % (data['name'], getItem(data['ship_type_id']).name),
            "Confirm Delete", wx.YES | wx.NO | wx.ICON_QUESTION
        ) as dlg:
            if dlg.ShowModal() == wx.ID_YES:
                activeChar = self.getActiveCharacter()
                if activeChar is None:
                    return
                try:
                    sEsi.delFitting(activeChar, data['fitting_id'])
                    # repopulate the fitting list
                    self.fitTree.populateSkillTree(self.fittings)
                    self.fitView.update([])
                except requests.exceptions.ConnectionError:
                    msg = "Connection error, please check your internet connection"
                    pyfalog.error(msg)
                    self.statusbar.SetStatusText(msg)


class ESIServerExceptionHandler:
    def __init__(self, parentWindow, ex):
        pyfalog.error(ex)
        with wx.MessageDialog(
            parentWindow,
            "There was an issue starting up the localized server, try setting "
            "Login Authentication Method to Manual by going to Preferences -> EVE SS0 -> "
            "Login Authentication Method. If this doesn't fix the problem please file an "
            "issue on Github.",
            "Add Character Error",
            wx.OK | wx.ICON_ERROR
        ) as dlg:
            dlg.ShowModal()


class ESIExceptionHandler:
    # todo: make this a generate excetpion handler for all calls
    def __init__(self, parentWindow, ex):
        if ex.response['error'].startswith('Token is not valid') or ex.response['error'] == 'invalid_token':  # todo: this seems messy, figure out a better response
            pyfalog.error(ex)
            with wx.MessageDialog(
                parentWindow,
                "There was an error validating characters' SSO token. Please try "
                "logging into the character again to reset the token.",
                "Invalid Token",
                wx.OK | wx.ICON_ERROR
            ) as dlg:
                dlg.ShowModal()
        else:
            # We don't know how to handle the error, raise it for the global error handler to pick it up
            raise ex


class ExportToEve(AuxiliaryFrame):

    def __init__(self, parent):
        super().__init__(
            parent, id=wx.ID_ANY, title="Export fit to EVE", pos=wx.DefaultPosition,
            size=wx.Size(400, 120) if "wxGTK" in wx.PlatformInfo else wx.Size(350, 100), resizeable=True)

        self.mainFrame = parent

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        hSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.charChoice = wx.Choice(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [])
        hSizer.Add(self.charChoice, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.updateCharList()
        self.charChoice.SetSelection(0)

        self.exportBtn = wx.Button(self, wx.ID_ANY, "Export Fit", wx.DefaultPosition, wx.DefaultSize, 5)
        hSizer.Add(self.exportBtn, 0, wx.ALL, 5)

        mainSizer.Add(hSizer, 0, wx.EXPAND, 5)

        self.exportBtn.Bind(wx.EVT_BUTTON, self.exportFitting)

        self.statusbar = wx.StatusBar(self)
        self.statusbar.SetFieldsCount(2)
        self.statusbar.SetStatusWidths([100, -1])

        self.Bind(wx.EVT_CHAR_HOOK, self.kbEvent)

        self.SetSizer(mainSizer)
        self.SetStatusBar(self.statusbar)
        self.Layout()
        self.SetMinSize(self.GetSize())

        self.Center(wx.BOTH)

    def updateCharList(self):
        sEsi = Esi.getInstance()
        chars = sEsi.getSsoCharacters()

        self.charChoice.Clear()
        for char in chars:
            self.charChoice.Append(char.characterName, char.ID)

        if len(chars) > 0:
            self.charChoice.SetSelection(0)

    def kbEvent(self, event):
        keycode = event.GetKeyCode()
        mstate = wx.GetMouseState()
        if keycode == wx.WXK_ESCAPE and mstate.GetModifiers() == wx.MOD_NONE:
            self.Close()
            return
        event.Skip()

    def getActiveCharacter(self):
        selection = self.charChoice.GetCurrentSelection()
        return self.charChoice.GetClientData(selection) if selection not in (None, -1) else None

    def exportFitting(self, event):
        sPort = Port.getInstance()
        fitID = self.mainFrame.getActiveFit()

        self.statusbar.SetStatusText("", 0)

        if fitID is None:
            self.statusbar.SetStatusText("Please select an active fitting in the main window", 1)
            return

        self.statusbar.SetStatusText("Sending request and awaiting response", 1)
        sEsi = Esi.getInstance()

        sFit = Fit.getInstance()
        try:
            data = sPort.exportESI(sFit.getFit(fitID))
        except ESIExportException as e:
            msg = str(e)
            if not msg:
                msg = "Failed to generate export data"
            pyfalog.warning(msg)
            self.statusbar.SetStatusText(msg, 1)
            return
        activeChar = self.getActiveCharacter()
        if activeChar is None:
            msg = "Need at least one ESI character to export"
            pyfalog.warning(msg)
            self.statusbar.SetStatusText(msg, 1)
            return
        res = sEsi.postFitting(activeChar, data)

        try:
            res.raise_for_status()
            self.statusbar.SetStatusText("", 0)
            self.statusbar.SetStatusText(res.reason, 1)
        except requests.exceptions.ConnectionError:
            msg = "Connection error, please check your internet connection"
            pyfalog.error(msg)
            self.statusbar.SetStatusText("ERROR", 0)
            self.statusbar.SetStatusText(msg, 1)
        except ESIExportException as ex:
            pyfalog.error(ex)
            self.statusbar.SetStatusText("ERROR", 0)
            self.statusbar.SetStatusText("{} - {}".format(res.status_code, res.reason), 1)
        except APIException as ex:
            try:
                ESIExceptionHandler(self, ex)
            except Exception as ex:
                self.statusbar.SetStatusText("ERROR", 0)
                self.statusbar.SetStatusText("{} - {}".format(res.status_code, res.reason), 1)
                pyfalog.error(ex)


class SsoCharacterMgmt(AuxiliaryFrame):

    def __init__(self, parent):
        super().__init__(
            parent, id=wx.ID_ANY, title="SSO Character Management", pos=wx.DefaultPosition,
            size=wx.Size(550, 250), resizeable=True)
        self.mainFrame = parent
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.lcCharacters = wx.ListCtrl(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LC_REPORT)

        self.lcCharacters.InsertColumn(0, heading='Character')
        self.lcCharacters.InsertColumn(1, heading='Character ID')

        self.popCharList()

        mainSizer.Add(self.lcCharacters, 1, wx.ALL | wx.EXPAND, 5)

        btnSizer = wx.BoxSizer(wx.VERTICAL)

        self.addBtn = wx.Button(self, wx.ID_ANY, "Add Character", wx.DefaultPosition, wx.DefaultSize, 0)
        btnSizer.Add(self.addBtn, 0, wx.ALL | wx.EXPAND, 5)

        self.deleteBtn = wx.Button(self, wx.ID_ANY, "Revoke Character", wx.DefaultPosition, wx.DefaultSize, 0)
        btnSizer.Add(self.deleteBtn, 0, wx.ALL | wx.EXPAND, 5)

        mainSizer.Add(btnSizer, 0, wx.EXPAND, 5)

        self.addBtn.Bind(wx.EVT_BUTTON, self.addChar)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.delChar)

        self.mainFrame.Bind(GE.EVT_SSO_LOGIN, self.ssoLogin)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_CHAR_HOOK, self.kbEvent)

        self.SetSizer(mainSizer)
        self.Layout()
        self.SetMinSize(self.GetSize())

        self.Centre(wx.BOTH)

    def ssoLogin(self, event):
        self.popCharList()
        event.Skip()

    def kbEvent(self, event):
        keycode = event.GetKeyCode()
        mstate = wx.GetMouseState()
        if keycode == wx.WXK_ESCAPE and mstate.GetModifiers() == wx.MOD_NONE:
            self.Close()
            return
        event.Skip()

    def OnClose(self, event):
        self.mainFrame.Unbind(GE.EVT_SSO_LOGIN, handler=self.ssoLogin)
        event.Skip()

    def popCharList(self):
        sEsi = Esi.getInstance()
        chars = sEsi.getSsoCharacters()

        self.lcCharacters.DeleteAllItems()

        for index, char in enumerate(chars):
            self.lcCharacters.InsertItem(index, char.characterName)
            self.lcCharacters.SetItem(index, 1, str(char.characterID))
            self.lcCharacters.SetItemData(index, char.ID)

        self.lcCharacters.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.lcCharacters.SetColumnWidth(1, wx.LIST_AUTOSIZE)

    def addChar(self, event):
        try:
            sEsi = Esi.getInstance()
            sEsi.login()
        except Exception as ex:
            ESIServerExceptionHandler(self, ex)

    def delChar(self, event):
        item = self.lcCharacters.GetFirstSelected()
        if item > -1:
            charID = self.lcCharacters.GetItemData(item)
            sEsi = Esi.getInstance()
            sEsi.delSsoCharacter(charID)
            self.popCharList()


class FittingsTreeView(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.parent = parent
        pmainSizer = wx.BoxSizer(wx.VERTICAL)

        tree = self.fittingsTreeCtrl = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        pmainSizer.Add(tree, 1, wx.EXPAND | wx.ALL, 0)

        self.root = tree.AddRoot("Fits")
        self.populateSkillTree(None)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.displayFit)

        self.SetSizer(pmainSizer)

        self.Layout()

    def populateSkillTree(self, data):
        if data is None:
            return
        root = self.root
        tree = self.fittingsTreeCtrl
        tree.DeleteChildren(root)

        sEsi = Esi.getInstance()

        dict = {}
        fits = data
        for fit in fits:
            if fit['fitting_id'] in sEsi.fittings_deleted:
                continue
            ship = getItem(fit['ship_type_id'])
            if ship is None:
                pyfalog.debug('Cannot find ship type id: {}'.format(fit['ship_type_id']))
                continue
            if ship.name not in dict:
                dict[ship.name] = []
            dict[ship.name].append(fit)

        for name, fits in dict.items():
            shipID = tree.AppendItem(root, name)
            for fit in fits:
                fitId = tree.AppendItem(shipID, fit['name'])
                tree.SetItemData(fitId, json.dumps(fit))

        tree.SortChildren(root)

    def displayFit(self, event):
        selection = self.fittingsTreeCtrl.GetSelection()
        data = self.fittingsTreeCtrl.GetItemData(selection)

        if data is None:
            event.Skip()
            return

        fit = json.loads(data)
        list = []

        for item in fit['items']:
            try:
                cargo = Cargo(getItem(item['type_id']))
                cargo.amount = item['quantity']
                list.append(cargo)
            except Exception as e:
                pyfalog.critical("Exception caught in displayFit")
                pyfalog.critical(e)

        self.parent.fitView.fitSelection = selection
        self.parent.fitView.update(list)


class FitView(Display):
    DEFAULT_COLS = ["Base Icon",
                    "Base Name"]

    def __init__(self, parent):
        Display.__init__(self, parent, style=wx.LC_SINGLE_SEL)
        self.fitSelection = None
