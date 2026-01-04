class ConnectivityDialog(QDialog):
    """
    Popup Window for displaying Connectivity Plots.
    Uses its own FigureCanvas to show the circular graph.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connectivity Explorer")
        self.resize(800, 800)
        self.layout = QVBoxLayout(self)
        self.canvas = None
        
        # Add a "Close" button at the bottom
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.layout.addWidget(self.btn_close)

    def plot(self, fig):
        """Displays the given Matplotlib Figure."""
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
        
        self.canvas = FigureCanvasQTAgg(fig)
        self.layout.insertWidget(0, self.canvas) # Insert at top
        
        # Style
        fig.patch.set_facecolor('#2b2b2b') # Dark background match
        self.canvas.draw()
