"""
Visualization module for Eye Movement Assessment.
Generates trajectory plots and visual analysis of gaze data.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for embedding
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from typing import List, Tuple, Optional
from dataclasses import dataclass
import io


@dataclass
class TrajectoryPlotConfig:
    """Configuration for trajectory plots."""
    figsize: Tuple[int, int] = (10, 6)
    dpi: int = 100
    gaze_color: str = '#3498db'
    target_color: str = '#e74c3c'
    gaze_alpha: float = 0.7
    target_alpha: float = 0.5
    line_width: float = 1.5
    marker_size: float = 3
    show_velocity_color: bool = True
    velocity_cmap: str = 'viridis'


class TrajectoryVisualizer:
    """Generates trajectory visualizations from test results."""
    
    def __init__(self, config: Optional[TrajectoryPlotConfig] = None):
        """
        Initialize the visualizer.
        
        Args:
            config: Plot configuration options
        """
        self.config = config or TrajectoryPlotConfig()
    
    def plot_xy_trajectory(
        self,
        gaze_x: List[float],
        gaze_y: List[float],
        target_x: List[float],
        target_y: List[float],
        timestamps: Optional[List[float]] = None,
        title: str = "Gaze Trajectory"
    ) -> Figure:
        """
        Create XY trajectory plot showing gaze path vs target path.
        
        Args:
            gaze_x: Gaze X positions
            gaze_y: Gaze Y positions
            target_x: Target X positions
            target_y: Target Y positions
            timestamps: Optional timestamps for velocity coloring
            title: Plot title
            
        Returns:
            Matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=self.config.figsize, dpi=self.config.dpi)
        
        # Plot target path
        ax.plot(target_x, target_y, 
                color=self.config.target_color, 
                alpha=self.config.target_alpha,
                linewidth=self.config.line_width * 1.5,
                label='Target', linestyle='--')
        
        # Plot gaze path with velocity coloring if timestamps provided
        if self.config.show_velocity_color and timestamps and len(timestamps) > 1:
            # Calculate velocity
            velocities = self._calculate_velocities(gaze_x, gaze_y, timestamps)
            
            # Create line segments colored by velocity
            points = np.array([gaze_x, gaze_y]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            
            from matplotlib.collections import LineCollection
            norm = plt.Normalize(0, np.percentile(velocities, 95))
            lc = LineCollection(segments, cmap=self.config.velocity_cmap, norm=norm)
            lc.set_array(velocities)
            lc.set_linewidth(self.config.line_width)
            lc.set_alpha(self.config.gaze_alpha)
            ax.add_collection(lc)
            
            # Add colorbar
            cbar = fig.colorbar(lc, ax=ax, label='Velocity (px/s)')
        else:
            ax.plot(gaze_x, gaze_y,
                    color=self.config.gaze_color,
                    alpha=self.config.gaze_alpha,
                    linewidth=self.config.line_width,
                    label='Gaze')
        
        # Mark start and end
        if gaze_x and gaze_y:
            ax.scatter([gaze_x[0]], [gaze_y[0]], color='green', s=50, zorder=5, label='Start')
            ax.scatter([gaze_x[-1]], [gaze_y[-1]], color='red', s=50, zorder=5, label='End')
        
        ax.set_xlabel('X Position (pixels)')
        ax.set_ylabel('Y Position (pixels)')
        ax.set_title(title)
        ax.legend(loc='upper right')
        ax.invert_yaxis()  # Screen coordinates
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def plot_time_series(
        self,
        gaze_x: List[float],
        gaze_y: List[float],
        target_x: List[float],
        target_y: List[float],
        timestamps: List[float],
        title: str = "Position vs Time"
    ) -> Figure:
        """
        Create time series plot showing X and Y positions over time.
        
        Args:
            gaze_x: Gaze X positions
            gaze_y: Gaze Y positions
            target_x: Target X positions
            target_y: Target Y positions
            timestamps: Timestamps in seconds
            title: Plot title
            
        Returns:
            Matplotlib Figure object
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.config.figsize, 
                                        dpi=self.config.dpi, sharex=True)
        
        # Normalize timestamps to start at 0
        t = np.array(timestamps) - timestamps[0]
        
        # X position
        ax1.plot(t, target_x, color=self.config.target_color, 
                 alpha=self.config.target_alpha, linewidth=self.config.line_width,
                 label='Target X', linestyle='--')
        ax1.plot(t, gaze_x, color=self.config.gaze_color,
                 alpha=self.config.gaze_alpha, linewidth=self.config.line_width,
                 label='Gaze X')
        ax1.set_ylabel('X Position (px)')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_title(title)
        
        # Y position
        ax2.plot(t, target_y, color=self.config.target_color,
                 alpha=self.config.target_alpha, linewidth=self.config.line_width,
                 label='Target Y', linestyle='--')
        ax2.plot(t, gaze_y, color=self.config.gaze_color,
                 alpha=self.config.gaze_alpha, linewidth=self.config.line_width,
                 label='Gaze Y')
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Y Position (px)')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _calculate_velocities(
        self,
        x: List[float],
        y: List[float],
        timestamps: List[float]
    ) -> np.ndarray:
        """Calculate velocity at each point."""
        x = np.array(x)
        y = np.array(y)
        t = np.array(timestamps)
        
        # Calculate displacement
        dx = np.diff(x)
        dy = np.diff(y)
        dt = np.diff(t)
        
        # Avoid division by zero
        dt = np.maximum(dt, 1e-6)
        
        # Velocity magnitude
        velocity = np.sqrt(dx**2 + dy**2) / dt
        
        return velocity
    
    def plot_heatmap(
        self,
        gaze_x: List[float],
        gaze_y: List[float],
        screen_width: int = 1920,
        screen_height: int = 1080,
        bins: int = 50,
        title: str = "Gaze Heatmap"
    ) -> Figure:
        """
        Create gaze density heatmap.
        
        Args:
            gaze_x: Gaze X positions
            gaze_y: Gaze Y positions
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
            bins: Number of bins for histogram
            title: Plot title
            
        Returns:
            Matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=self.config.figsize, dpi=self.config.dpi)
        
        # Create 2D histogram
        x = np.array(gaze_x)
        y = np.array(gaze_y)
        
        # Create heatmap
        heatmap, xedges, yedges = np.histogram2d(
            x, y, bins=bins,
            range=[[0, screen_width], [0, screen_height]]
        )
        
        # Apply Gaussian smoothing
        from scipy.ndimage import gaussian_filter
        heatmap = gaussian_filter(heatmap.T, sigma=2)
        
        # Plot
        extent = [0, screen_width, screen_height, 0]
        im = ax.imshow(
            heatmap, extent=extent, origin='upper',
            cmap='hot', alpha=0.8, aspect='auto'
        )
        
        # Add colorbar
        cbar = fig.colorbar(im, ax=ax, label='Gaze Density')
        
        # Calculate and mark centroid
        if len(x) > 0:
            centroid_x = np.mean(x)
            centroid_y = np.mean(y)
            ax.scatter([centroid_x], [centroid_y], color='cyan', s=100, 
                      marker='+', linewidths=2, label='Centroid', zorder=5)
            ax.legend(loc='upper right')
        
        ax.set_xlabel('X Position (pixels)')
        ax.set_ylabel('Y Position (pixels)')
        ax.set_title(title)
        ax.set_xlim(0, screen_width)
        ax.set_ylim(screen_height, 0)
        
        plt.tight_layout()
        return fig

    def figure_to_image(self, fig: Figure) -> bytes:
        """
        Convert matplotlib figure to PNG bytes.
        
        Args:
            fig: Matplotlib Figure
            
        Returns:
            PNG image as bytes
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        return buf.getvalue()
    
    def save_figure(self, fig: Figure, filepath: str):
        """
        Save figure to file.
        
        Args:
            fig: Matplotlib Figure
            filepath: Output file path (supports .png, .svg, .pdf)
        """
        fig.savefig(filepath, bbox_inches='tight', facecolor='white', dpi=self.config.dpi)
        plt.close(fig)


def generate_trajectory_from_result(result, visualizer: Optional[TrajectoryVisualizer] = None) -> Tuple[Figure, Figure]:
    """
    Generate trajectory plots from a TestResult.
    
    Args:
        result: TestResult object
        visualizer: Optional TrajectoryVisualizer instance
        
    Returns:
        Tuple of (XY trajectory figure, time series figure)
    """
    if visualizer is None:
        visualizer = TrajectoryVisualizer()
    
    # Extract data from frames
    gaze_x = []
    gaze_y = []
    target_x = []
    target_y = []
    timestamps = []
    
    for frame in result.frames:
        if frame.gaze_x is not None and frame.gaze_y is not None:
            gaze_x.append(frame.gaze_x)
            gaze_y.append(frame.gaze_y)
            target_x.append(frame.target_x)
            target_y.append(frame.target_y)
            timestamps.append(frame.timestamp)
    
    if not gaze_x:
        raise ValueError("No valid gaze data in result")
    
    # Generate plots
    xy_fig = visualizer.plot_xy_trajectory(
        gaze_x, gaze_y, target_x, target_y, timestamps,
        title=f"Gaze Trajectory - {result.pattern.value}"
    )
    
    time_fig = visualizer.plot_time_series(
        gaze_x, gaze_y, target_x, target_y, timestamps,
        title=f"Position vs Time - {result.pattern.value}"
    )
    
    return xy_fig, time_fig
