"""
Matplotlib Canvas Module

Contains the MplCanvas class for embedding Matplotlib figures in PyQt6.
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class MplCanvas(FigureCanvasQTAgg):
    """
    Matplotlib canvas widget for PyQt6 integration.
    Uses dark background styling for consistency with the application theme.
    """

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.axes.set_facecolor('#1e1e1e')

        super(MplCanvas, self).__init__(self.fig)
