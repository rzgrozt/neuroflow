"""Matplotlib Canvas for PyQt6 integration."""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


import numpy as np

class MplCanvas(FigureCanvasQTAgg):
    """Matplotlib canvas widget with dark theme styling."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#1e1e1e')
        self.axes.set_facecolor('#1e1e1e')

        super(MplCanvas, self).__init__(self.fig)

    def plot_time_series(self, data, title, overlay_data=None, start_time=0.0, 
                         duration=10.0, scale=50.0, n_channels=None):
        """
        Plot time-series in clinical stacked view with navigation support.
        
        Parameters
        ----------
        data : mne.io.Raw or mne.Epochs
            The processed MNE Raw or Epochs object to display.
        title : str
            Title for the plot.
        overlay_data : mne.io.Raw, optional
            Original raw data to overlay in background for comparison.
        start_time : float
            Start time in seconds for the viewing window.
        duration : float
            Duration in seconds to display (default 10s).
        scale : float
            Amplitude scale in microvolts (default 50uV). Controls vertical spacing.
        n_channels : int, optional
            Number of channels to display. If None, shows all channels.
        """
        from mne import BaseEpochs
        
        self.axes.clear()
        
        if data is None:
            self.axes.text(
                0.5, 0.5, 'No data available',
                color='#606080', ha='center', va='center', fontsize=14
            )
            self.draw()
            return
        
        is_epochs = isinstance(data, BaseEpochs)
        
        # Extract data parameters
        sfreq = data.info['sfreq']
        ch_names = data.ch_names
        
        if is_epochs:
            # For epochs, show the average across all epochs
            times = data.times
            total_duration = times[-1] - times[0]
            # Get averaged data across epochs (channels × times)
            raw_array = data.get_data().mean(axis=0)  # Average across epochs
            # For epochs, use the full epoch time range (which may include negative times)
            epoch_tmin = times[0]
            epoch_tmax = times[-1]
        else:
            total_duration = data.times[-1]
            times = None  # Will be set after slicing
            raw_array = None
            epoch_tmin = 0
            epoch_tmax = total_duration

        # Clamp start_time to valid range
        if is_epochs:
            # For epochs, always show the full epoch (ignore start_time/duration navigation)
            start_time = epoch_tmin
            end_time = epoch_tmax
        else:
            start_time = max(0, min(start_time, total_duration - duration))
            end_time = min(start_time + duration, total_duration)
        
        # Limit channels if specified
        if n_channels is not None:
            n_channels = min(n_channels, len(ch_names))
        else:
            n_channels = len(ch_names)
        
        # Downsample for performance if data is large
        max_points = 5000
        
        if is_epochs:
            # For epochs, use the full time array (already set to epoch times)
            # No slicing needed - show the complete epoch
            times = data.times
            raw_array = raw_array[:n_channels, :]

            total_samples = len(times)
            decim_factor = max(1, total_samples // max_points)
            times = times[::decim_factor]
            raw_array = raw_array[:, ::decim_factor]
        else:
            # Calculate sample indices for raw data
            start_sample = int(start_time * sfreq)
            end_sample = int(end_time * sfreq)
            
            total_samples = end_sample - start_sample
            decim_factor = max(1, total_samples // max_points)
            
            # Get the raw data array for selected channels
            raw_array, times = data[:n_channels, start_sample:end_sample]
            times = times[::decim_factor]
            raw_array = raw_array[:, ::decim_factor]
        
        # Convert to microvolts
        raw_array_uv = raw_array * 1e6
        
        # Calculate offset based on scale (each channel gets 2*scale spacing)
        channel_spacing = 2 * scale
        offsets = np.arange(n_channels) * channel_spacing
        
        # Plot overlay data first (background) if provided (only for raw data)
        if overlay_data is not None and not is_epochs:
            start_sample = int(start_time * sfreq)
            end_sample = int(end_time * sfreq)
            overlay_array, _ = overlay_data[:n_channels, start_sample:end_sample]
            overlay_array = overlay_array[:, ::decim_factor]
            overlay_array_uv = overlay_array * 1e6
            
            # Plot overlay channels in red with transparency
            for i in range(n_channels):
                # Center the data and apply offset (inverted so ch0 is at top)
                ch_data = overlay_array_uv[i, :] - np.mean(overlay_array_uv[i, :])
                y_values = ch_data + offsets[n_channels - 1 - i]
                self.axes.plot(
                    times, y_values,
                    color='red', alpha=0.5, linewidth=0.6
                )
        
        # Plot processed data (foreground) in cyan/white
        for i in range(n_channels):
            # Center the data and apply offset (inverted so ch0 is at top)
            ch_data = raw_array_uv[i, :] - np.mean(raw_array_uv[i, :])
            y_values = ch_data + offsets[n_channels - 1 - i]
            self.axes.plot(
                times, y_values,
                color='#00ffff', linewidth=0.7
            )
        
        # Set up Y-axis with channel names (inverted order)
        self.axes.set_yticks(offsets)
        self.axes.set_yticklabels(list(reversed(ch_names[:n_channels])), fontsize=7)
        
        # Styling - Clinical EEG look
        self.axes.set_title(title, color='white', pad=10, fontsize=10)
        self.axes.set_xlabel('Time (s)', color='white')
        self.axes.set_ylabel('', color='white')  # Channel names are the labels
        self.axes.tick_params(axis='x', colors='white')
        self.axes.tick_params(axis='y', colors='white', length=0)  # Hide tick marks
        self.axes.set_facecolor('#1e1e1e')
        
        # Set axis limits
        self.axes.set_xlim(times[0], times[-1])
        self.axes.set_ylim(-channel_spacing, offsets[-1] + channel_spacing)
        
        # Subtle vertical grid lines only
        self.axes.grid(True, linestyle='-', alpha=0.1, axis='x', color='white')
        self.axes.grid(False, axis='y')
        
        # Add scale bar indicator in corner
        scale_text = f"Scale: {scale:.0f} µV"
        if is_epochs:
            scale_text += f" (Avg of {len(data)} epochs)"
        self.axes.text(
            0.98, 0.02, scale_text,
            transform=self.axes.transAxes,
            color='#888888', fontsize=8,
            ha='right', va='bottom'
        )
        
        self.fig.tight_layout()
        self.draw()
