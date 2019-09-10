import gui.mainFrame
from eos.saveddata.targetProfile import TargetProfile
from graphs.wrapper import TargetWrapper
from gui.contextMenu import ContextMenuSingle
from gui.targetProfileEditor import TargetProfileEditor


class TargetProfileEditorMenu(ContextMenuSingle):

    def __init__(self):
        self.mainFrame = gui.mainFrame.MainFrame.getInstance()

    def display(self, callingWindow, srcContext, mainItem):
        if srcContext != 'graphTgtList':
            return False
        if not isinstance(mainItem, TargetWrapper):
            return False
        if not mainItem.isProfile:
            return False
        if mainItem.item is TargetProfile.getIdeal():
            return False
        return True

    def getText(self, callingWindow, itmContext, mainItem):
        return 'Edit Target Profile'

    def activate(self, callingWindow, fullContext, mainItem, i):
        TargetProfileEditor.openOne(parent=self.mainFrame, selected=mainItem.item)


TargetProfileEditorMenu.register()
