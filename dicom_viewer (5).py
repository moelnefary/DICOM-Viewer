import os
import sys
import pydicom
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog, 
                             QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
                             QSlider, QMessageBox, QComboBox, QDialog, 
                             QListWidget, QListWidgetItem,QScrollArea, QGridLayout)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QProgressDialog, QTextEdit, QFileDialog, 
                             QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
                             QSlider, QMessageBox, QComboBox, QDialog, 
                             QListWidget, QListWidgetItem)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from faker import Faker
import random
import pydicom.datadict as datadict
from matplotlib.figure import Figure
from PyQt5.QtCore import QTimer
class TilesDialog(QDialog):
    def __init__(self, dicom_handler, parent=None):
        super().__init__(parent)
        self.dicom_handler = dicom_handler
        self.setWindowTitle('DICOM Folder Tiles')
        self.setGeometry(100, 100, 1000, 800)

        # Main layout
        main_layout = QVBoxLayout()

        # Scroll area for tiles
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Widget to hold the grid of tiles
        tiles_widget = QWidget()
        grid_layout = QGridLayout(tiles_widget)

        # Create tiles for each DICOM image
        update_index= len(self.dicom_handler.current_datasets)/30
        for i, dataset in enumerate(self.dicom_handler.current_datasets[::]):
            try:
                # Get pixel array and create thumbnail
                pixel_array = dataset.pixel_array

                # Resize to a standard thumbnail size
                thumbnail = self.create_thumbnail(pixel_array, (200, 200))

                # Create a label with the thumbnail
                tile_label = QLabel()
                tile_label.setPixmap(thumbnail)
                tile_label.setToolTip(f"Image {i * 5 + 1}")

                # Add hover effect
                tile_label.setStyleSheet("""
                    QLabel { 
                        border: 2px solid transparent; 
                        padding: 5px; 
                    }
                    QLabel:hover { 
                        border: 2px solid blue; 
                    }
                """)

                # Calculate grid position
                row = i // 5  # 5 tiles per row
                col = i % 5

                grid_layout.addWidget(tile_label, row, col)

                # Add click event to switch to this image in main viewer
                tile_label.mousePressEvent = lambda event, index=i * 5: self.select_image(index)
            

                
            
            except Exception as e:
                print(f"Could not create tile for image {i}: {e}")

        # Set the grid layout to the scroll area widget
        scroll_area.setWidget(tiles_widget)

        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)

        # Close button
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

        self.setLayout(main_layout)

    def create_thumbnail(self, pixel_array, size):
        """
        Create a thumbnail from the pixel array
        
        Args:
            pixel_array (numpy.ndarray): Input image array
            size (tuple): Desired thumbnail size
        
        Returns:
            QPixmap: Thumbnail image
        """
        # Normalize the pixel array
        normalized = ((pixel_array - pixel_array.min()) / 
                      (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        
        # Create QImage
        height, width = normalized.shape
        bytes_per_line = width
        q_img = QImage(normalized.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        
        # Convert to pixmap and scale
        pixmap = QPixmap.fromImage(q_img)
        return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def select_image(self, index):
        """
        Close the tiles dialog and update the main viewer to the selected image
        
        Args:
            index (int): Index of the selected image
        """
        # If parent exists and is the main viewer, update the slider
        if self.parent():
            self.parent().image_slider.setValue(index)
        self.close() 

class ExploreDialog(QDialog):
   def __init__(self, data, title):
        super().__init__()
        self.setWindowTitle(f'Explore {title}')
        self.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        
        # Create label to explain the data
        title_label = QLabel(f"{title} Details for Current Image:")
        layout.addWidget(title_label)
        
        # Create table widget instead of list
        self.details_table = QTableWidget()
        self.details_table.setColumnCount(2)
        self.details_table.setHorizontalHeaderLabels(['Attribute', 'Value'])
        
        # Populate table
        self.details_table.setRowCount(len(data))
        for row, (key, value) in enumerate(data.items()):
            self.details_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.details_table.setItem(row, 1, QTableWidgetItem(str(value)))
        
        self.details_table.resizeColumnsToContents()
        layout.addWidget(self.details_table)
        
        # Add total count label
        count_label = QLabel(f"Total Attributes: {len(data)}")
        layout.addWidget(count_label)
        
        self.setLayout(layout)
        
class DicomFolderHandler:
    def __init__(self):
        self.dicom_files = []
        self.current_datasets = []
        self.faker = Faker()

    def load_dicom_folder(self, folder_path):
        """
        Load all DICOM files from a given folder
        
        Args:
            folder_path (str): Path to the folder containing DICOM files
        
        Returns:
            list: List of loaded DICOM file paths
        """
        self.dicom_files = []
        self.current_datasets = []
        
        # Recursively find all .dcm files
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.dcm'):
                    full_path = os.path.join(root, file)
                    try:
                        ds = pydicom.dcmread(full_path)
                        self.dicom_files.append(full_path)
                        self.current_datasets.append(ds)
                    except Exception as e:
                        print(f"Could not read {full_path}: {e}")
        
        return self.dicom_files

    def get_image_at_index(self, index):
        """
        Get pixel array for a specific DICOM file
        
        Args:
            index (int): Index of the DICOM file
        
        Returns:
            numpy.ndarray: Pixel data
        """
        if 0 <= index < len(self.current_datasets):
            return self.current_datasets[index].pixel_array
        return None

    def get_dicom_tags(self, index):
        if 0 <= index < len(self.current_datasets):
            dataset = self.current_datasets[index]
            tags_dict = {}
            
            for elem in dataset:
                tag_hex = elem.tag
                
                try:
                    tag_name = datadict.keyword_for_tag(tag_hex)
                    
                    if not tag_name:
                        tag_name = str(tag_hex)
                except:
                    tag_name = str(tag_hex)
                
                if not tag_name:
                    tag_name = str(tag_hex)
                
                try:
                    # Special handling for sequence types
                    if elem.VR == 'SQ':
                        value = f"Sequence (length {len(elem.value)})"
                    else:
                        value = str(elem.value)
                    
                    # Swap Patient Name and Patient ID values
                    if tag_name == 'PatientName':
                        # Find Patient ID tag
                        for other_elem in dataset:
                            if datadict.keyword_for_tag(other_elem.tag) == 'PatientID':
                                value = str(other_elem.value)
                                break
                    elif tag_name == 'PatientID':
                        # Find Patient Name tag
                        for other_elem in dataset:
                            if datadict.keyword_for_tag(other_elem.tag) == 'PatientName':
                                value = str(other_elem.value)
                                break
                except:
                    value = "Unable to decode"
                
                tags_dict[tag_name] = value
            
            return tags_dict
        return{}

    def anonymize_file(self, index, prefix):
        """
        Anonymize a specific DICOM file
        
        Args:
            index (int): Index of the DICOM file
            prefix (str): Prefix for anonymized values
        
        Returns:
            dict: Anonymized tags
        """
        if 0 <= index < len(self.current_datasets):
            dataset = self.current_datasets[index]
            
            # Key tags to anonymize with human-readable equivalents
            anonymization_map = {
                'PatientName': f"{prefix}_{self.faker.last_name()}",
                'PatientID': f"{prefix}_{random.randint(10000, 99999)}",
                'PatientBirthDate': self.faker.date_of_birth().strftime("%Y%m%d"),
                'StudyInstanceUID': f"{prefix}_{self.faker.uuid4()}",
                'ReferringPhysicianName': f"{prefix}_{self.faker.name()}"
            }
            
            # Apply anonymization
            anonymized_tags = {}
            for tag_name, new_value in anonymization_map.items():
                try:
                    # Find the tag and update its value
                    for elem in dataset:
                        if datadict.keyword_for_tag(elem.tag) == tag_name:
                            elem.value = new_value
                            anonymized_tags[tag_name] = new_value
                            break
                except:
                    pass
            
            return anonymized_tags
        return {}
    def explore_data(self, explore_type):
        """
        Explore and extract specific types of DICOM metadata
        
        Args:
            explore_type (str): Type of metadata to explore
        
        Returns:
            list: List of actual metadata values
        """
        if not self.current_datasets:
            return []
        
        # Mapping of explore types to DICOM tag keywords
        explore_map = {
            'Patient': 'PatientName',
            'Study': 'StudyDescription',
            'Modality': 'Modality',
            'Physician': 'ReferringPhysicianName',
            'Institution': 'InstitutionName'
        }
        
        # Get the corresponding tag keyword
        tag_keyword = explore_map.get(explore_type)
        
        if not tag_keyword:
            return []
        
        # Collect values
        values = []
        for dataset in self.current_datasets:
            try:
                # Find the tag
                for elem in dataset:
                    if datadict.keyword_for_tag(elem.tag) == tag_keyword:
                        value = str(elem.value)
                        values.append(value)
                        break
            except:
                pass
        
        return values
    def anonymize_folder(self, prefix):
        """
        Anonymize all loaded DICOM files in the current dataset
    
        Args:
            prefix (str): Prefix for anonymized values
    
        Returns:
            list: List of anonymized tags for each file
        """
        if not self.current_datasets:
            return []
    
        # Key tags to anonymize with human-readable equivalents
        anonymization_map = {
            'PatientName': f"{prefix}_{self.faker.last_name()}",
            'PatientID': f"{prefix}_{random.randint(10000, 99999)}",
            'PatientBirthDate': self.faker.date_of_birth().strftime("%Y%m%d"),
            'StudyInstanceUID': f"{prefix}_{self.faker.uuid4()}",
            'ReferringPhysicianName': f"{prefix}_{self.faker.name()}"
        }
    
        # Collect anonymized tags for all files
        all_anonymized_tags = []
    
        # Anonymize each dataset
        for dataset in self.current_datasets:
            anonymized_tags_for_file = {}
        
            # Apply anonymization
            for tag_name, new_value in anonymization_map.items():
                try:
                    # Find the tag and update its value
                    for elem in dataset:
                        if datadict.keyword_for_tag(elem.tag) == tag_name:
                            elem.value = new_value
                            anonymized_tags_for_file[tag_name] = new_value
                            break
                except:
                    pass
        
            all_anonymized_tags.append(anonymized_tags_for_file)
    
        return all_anonymized_tags        
    def explore_single_image_data(self, index, explore_type):
        """
        Explore metadata for a specific single DICOM file
        
        Args:
            index (int): Index of the DICOM file
            explore_type (str): Type of metadata to explore
        
        Returns:
            dict: Dictionary of metadata values
        """
        if 0 > index or index >= len(self.current_datasets):
            return {}
        
        # Mapping of explore types to DICOM tag keywords
        explore_map = {
            'Patient': ['PatientName', 'PatientID', 'PatientBirthDate'],
            'Physician': ['ReferringPhysicianName', 'PerformingPhysicianName'],
            'Study': ['StudyDescription', 'StudyInstanceUID', 'AccessionNumber'],
            'Image Details': ['Rows', 'Columns', 'PixelSpacing', 'SliceThickness', 'ImagePosition']
        }
        
        # Get the corresponding tag keywords
        tag_keywords = explore_map.get(explore_type, [])
        
        # Get the specific dataset
        dataset = self.current_datasets[index]
        
        # Collect values
        values = {}
        try:
            # Find the tags
            for elem in dataset:
                tag_name = datadict.keyword_for_tag(elem.tag)
                if tag_name in tag_keywords:
                    try:
                        value = str(elem.value)
                        values[tag_name] = value
                    except:
                        values[tag_name] = "Unable to decode"
        except:
            pass
        
        return values




class DicomFolderViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dicom_handler = DicomFolderHandler()
        self.current_index = 0
        
        # Store zoom and pan state
        self.zoom_history = []
        
        # New attribute for multi-frame handling
        self.multi_frame_dataset = None
        
        self.initUI()

    def download_dicom_files(self):
        """
        Download DICOM files with current zoom levels
        """
        if not self.dicom_handler.dicom_files:
            QMessageBox.warning(self, 'No Files', 'No DICOM files loaded.')
            return

        # Ask user to select download directory
        download_dir = QFileDialog.getExistingDirectory(self, 'Select Download Directory')
    
        if not download_dir:
            return  # User cancelled

        try:
            # Create a progress dialog
            progress = QProgressDialog("Downloading DICOM files...", "Cancel", 0, len(self.dicom_handler.dicom_files), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Track successfully downloaded files
            downloaded_files = []

            # Iterate through all DICOM files
            for i, (file_path, dataset) in enumerate(zip(self.dicom_handler.dicom_files, self.dicom_handler.current_datasets)):
                # Check if user cancelled
                if progress.wasCanceled():
                    break

                # Generate new filename
                original_filename = os.path.basename(file_path)
                new_filename = f"modified_{original_filename}"
                new_file_path = os.path.join(download_dir, new_filename)

                try:
                    # Store zoom level if available
                    if hasattr(self, 'zoom_levels') and self.current_index in self.zoom_levels:
                        zoom_level = self.zoom_levels[self.current_index]
                        # Add a private tag to store zoom level as a float
                        dataset.add_new((0x0029, 0x1000), 'DS', str(zoom_level))

                    # Save the modified dataset
                    dataset.save_as(new_file_path)
                    downloaded_files.append(new_file_path)
                except Exception as save_error:
                    QMessageBox.warning(self, 'Save Error', f"Could not save {original_filename}: {save_error}")

                # Update progress
                progress.setValue(i + 1)

            # Close progress dialog
            progress.close()

            # Show summary
            if downloaded_files:
                QMessageBox.information(
                    self, 
                    'Download Complete', 
                    f'Successfully downloaded {len(downloaded_files)} DICOM files to {download_dir}'
                )
            else:
                QMessageBox.warning(self, 'Download', 'No files were downloaded.')

        except Exception as e:
            QMessageBox.critical(self, 'Download Error', f'An error occurred: {e}')

    def initUI(self):
        self.setWindowTitle('DICOM Folder Viewer')
        self.setGeometry(100, 100, 1400, 900)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Left panel for controls
        control_panel = QVBoxLayout()
        download_btn = QPushButton('Download Modified Files')
        download_btn.clicked.connect(self.download_dicom_files)
        control_panel.addWidget(download_btn)
    
        # Folder Open Button
        folder_btn = QPushButton('Open DICOM Folder')
        folder_btn.clicked.connect(self.open_dicom_folder)
        control_panel.addWidget(folder_btn)

        # Single File Open Button
        file_btn = QPushButton('Open DICOM File')
        file_btn.clicked.connect(self.open_single_dicom_file)
        control_panel.addWidget(file_btn)

        # Cine Button
        self.cine_btn = QPushButton('Start Cine')
        self.cine_btn.clicked.connect(self.toggle_cine_mode)
        control_panel.addWidget(self.cine_btn)
        # Folder Anonymization Button
        folder_anon_btn = QPushButton('Anonymize Folder')
        folder_anon_btn.clicked.connect(self.anonymize_dicom_folder)
        control_panel.addWidget(folder_anon_btn)

        # Image Slider
        slider_layout = QHBoxLayout()
        self.image_slider = QSlider(Qt.Horizontal)
        self.image_slider.valueChanged.connect(self.update_image)
        self.slider_label = QLabel('Image: 0/0')
        slider_layout.addWidget(self.image_slider)
        slider_layout.addWidget(self.slider_label)
        control_panel.addLayout(slider_layout)


        # Tag Search Section
        tag_search_layout = QHBoxLayout()
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText('Enter DICOM Tag')
        tag_search_btn = QPushButton('Search Tag')
        tag_search_btn.clicked.connect(self.search_dicom_tag)
        tag_search_layout.addWidget(self.tag_search_input)
        tag_search_layout.addWidget(tag_search_btn)
        control_panel.addLayout(tag_search_layout)

        # Anonymization Section
        anon_layout = QHBoxLayout()
        self.anon_prefix_input = QLineEdit()
        self.anon_prefix_input.setPlaceholderText('Anonymization Prefix')
        anon_btn = QPushButton('Anonymize Current')
        anon_btn.clicked.connect(self.anonymize_current_dicom)
        anon_layout.addWidget(self.anon_prefix_input)
        anon_layout.addWidget(anon_btn)
        control_panel.addLayout(anon_layout)

        # Tabs for display
        self.tabs = QTabWidget()
        self.image_tab = QWidget()
        self.tags_tab = QWidget()
        
        self.tabs.addTab(self.image_tab, "Image")
        self.tabs.addTab(self.tags_tab, "All Tags")

        # Image display layout
        image_layout = QVBoxLayout()
        self.figure = Figure(figsize=(10, 10), dpi=100)
        self.image_canvas = FigureCanvas(self.figure)
        
        # Connect mouse wheel event for zooming
        self.image_canvas.mpl_connect('scroll_event', self.on_scroll)
        
        image_layout.addWidget(self.image_canvas)
        self.image_tab.setLayout(image_layout)
        # Tags display layout
        tags_layout = QVBoxLayout()
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(2)
        self.tags_table.setHorizontalHeaderLabels(['Tag', 'Value'])
        tags_layout.addWidget(self.tags_table)
        self.tags_tab.setLayout(tags_layout)

        # Combine layouts
        main_layout.addLayout(control_panel, 1)
        main_layout.addWidget(self.tabs, 4)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        explore_layout = QHBoxLayout()
        self.explore_combo = QComboBox()
        self.explore_combo.addItems([
            'Patient', 
            'Physician', 
            'Study', 
            'Image Details'
        ])
        explore_btn = QPushButton('Explore')
        explore_btn.clicked.connect(self.explore_dicom_data)
        
        explore_layout.addWidget(self.explore_combo)
        explore_layout.addWidget(explore_btn)
        control_panel.addLayout(explore_layout)
         # [Rest of the initUI function]
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
         # Add Show Tiles button to the control panel
        tiles_btn = QPushButton('Show Tiles')
        tiles_btn.clicked.connect(self.show_dicom_tiles)
        control_panel.addWidget(tiles_btn)


        # Timer for Cine Mode
        self.cine_timer = QTimer(self)
        self.cine_timer.timeout.connect(self.next_image_cine)
        self.is_cine_mode = False
    def show_dicom_tiles(self):
        """
        Open a dialog to display tiles of loaded DICOM images
        """
        if not self.dicom_handler.dicom_files:
            QMessageBox.warning(self, 'No Files', 'Please load a DICOM folder first.')
            return

        # Open tiles dialog
        tiles_dialog = TilesDialog(self.dicom_handler, self)
        tiles_dialog.exec_()

    def load_multi_frame_dicom(self):
        """
        Load a multi-frame DICOM file and display it as a video-like sequence
        """
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select Multi-Frame DICOM File', '', 'DICOM Files (*.dcm)')
        if file_path:
            try:
                # Read the multi-frame DICOM dataset
                dataset = pydicom.dcmread(file_path)
                
                # Check if it's a multi-frame image
                if hasattr(dataset, 'NumberOfFrames') and int(dataset.NumberOfFrames) > 1:
                    num_frames = int(dataset.NumberOfFrames)
                    
                    # Clear previous state
                    self.multi_frame_dataset = dataset
                    self.dicom_handler.dicom_files = [file_path] * num_frames
                    self.dicom_handler.current_datasets = [dataset] * num_frames
                    
                    # Setup slider for frames
                    self.current_index = 0
                    self.image_slider.setMinimum(0)
                    self.image_slider.setMaximum(num_frames - 1)
                    self.image_slider.setValue(0)
                    self.slider_label.setText(f'Frame: 1/{num_frames}')
                    
                    # Display the first frame and tags
                    self.update_image()
                    self.display_tags()
                    
                    # Automatically start cine mode for multi-frame
                    self.cine_btn.setText('Pause Cine')
                    self.is_cine_mode = True
                    self.cine_timer.start(100)  # Faster timer for smoother video-like display
                else:
                    QMessageBox.warning(self, 'Not Multi-Frame', 'Selected DICOM file is not a multi-frame image.')
            
            except Exception as e:
                QMessageBox.critical(self, 'Error', f"Could not open multi-frame DICOM file: {e}")
    def toggle_cine_mode(self):
        """
        Start or stop cine mode for automatic image cycling.
        """
        if self.is_cine_mode:
            self.cine_timer.stop()
            self.cine_btn.setText('Start Cine')
            self.is_cine_mode = False
        else:
            self.cine_timer.start(500)  # Adjust interval (ms) for desired speed
            self.cine_btn.setText('Pause Cine')
            self.is_cine_mode = True

    def next_image_cine(self):
        """
        Advance to the next image in cine mode, wrapping around if needed.
        """
        if self.dicom_handler.dicom_files:
            current_value = self.image_slider.value()
            
            next_value = current_value + 1
        if next_value < len(self.dicom_handler.dicom_files):
            self.image_slider.setValue(next_value)  # This triggers update_image
        else:
            # Stop cine mode if needed, e.g., by disabling a timer or indicating completion
            self.toggle_cine_mode


    def open_single_dicom_file(self):
        """
        Allow the user to select and display a single DICOM file, 
        supporting both single and multi-frame images.
        """
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select DICOM File', '', 'DICOM Files (*.dcm)')
        if file_path:
            try:
                dataset = pydicom.dcmread(file_path)
                
                # Reset multi-frame dataset
                self.multi_frame_dataset = None
                
                # Check if it's a multi-frame image
                if hasattr(dataset, 'NumberOfFrames') and int(dataset.NumberOfFrames) > 1:
                    num_frames = int(dataset.NumberOfFrames)
                    
                    # Setup for multi-frame
                    self.multi_frame_dataset = dataset
                    self.dicom_handler.dicom_files = [file_path] * num_frames
                    self.dicom_handler.current_datasets = [dataset] * num_frames
                    
                    # Setup slider for frames
                    self.current_index = 0
                    self.image_slider.setMinimum(0)
                    self.image_slider.setMaximum(num_frames - 1)
                    self.image_slider.setValue(0)
                    self.slider_label.setText(f'Frame: 1/{num_frames}')
                    
                    # Automatically start cine mode for multi-frame
                    self.cine_btn.setText('Pause Cine')
                    self.is_cine_mode = True
                    self.cine_timer.start(100)  # Faster timer for smoother video-like display
                else:
                    # Setup for single-frame
                    self.dicom_handler.dicom_files = [file_path]
                    self.dicom_handler.current_datasets = [dataset]
                    self.current_index = 0
                    
                    # Update slider
                    self.image_slider.setMinimum(0)
                    self.image_slider.setMaximum(0)
                    self.image_slider.setValue(0)
                    self.slider_label.setText(f'Image: 1/1')
                    
                    # Stop cine mode if it was running
                    self.cine_timer.stop()
                    self.cine_btn.setText('Start Cine')
                    self.is_cine_mode = False

                # Display the image and tags
                self.update_image()
                self.display_tags()

            except Exception as e:
                QMessageBox.critical(self, 'Error', f"Could not open DICOM file: {e}")
    def on_scroll(self, event):
        """
        Handle mouse scroll events for zooming
        """
        # Check if we have an active plot
        if not event.inaxes:
            return
        
        # Current axes
        ax = event.inaxes
        
        # Get the current xlim and ylim
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()
        
        # Scaling factor
        xdata = event.xdata  # get event x location
        ydata = event.ydata  # get event y location
        
        if event.button == 'up':
            # Zoom in
            scale_factor = 0.9
        elif event.button == 'down':
            # Zoom out
            scale_factor = 1.1
        else:
            # Ignore other scroll events
            return

        # Calculate new limits
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        
        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])

        ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
        ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
        
        # Redraw the canvas
        self.image_canvas.draw_idle()

    def explore_dicom_data(self):
        """
        Open a dialog to explore selected metadata type for current image
        """
        if not self.dicom_handler.dicom_files:
            QMessageBox.warning(self, 'No Files', 'Please load a DICOM folder first.')
            return
        
        # Get selected explore type
        explore_type = self.explore_combo.currentText()
        
        # Get data for current image
        explore_data = self.dicom_handler.explore_single_image_data(
            self.current_index, explore_type
        )
        
        if explore_data:
            # Open explore dialog
            dialog = ExploreDialog(explore_data, explore_type)
            dialog.exec_()
        else:
            QMessageBox.information(self, 'No Data', f'No {explore_type} data found for current image.')

    def anonymize_dicom_folder(self):
        """
        Anonymize all loaded DICOM files in the current folder
        """
        if not self.dicom_handler.current_datasets:
            QMessageBox.warning(self, 'No Files', 'Please load a DICOM folder first.')
            return

        prefix = self.anon_prefix_input.text()
        if not prefix:
            QMessageBox.warning(self, 'Error', 'Please enter an anonymization prefix')
            return

        try:
            # Create a progress dialog
            progress = QProgressDialog("Anonymizing DICOM files...", "Cancel", 0, len(self.dicom_handler.current_datasets), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            # Anonymize the entire folder
            all_anonymized_tags = self.dicom_handler.anonymize_folder(prefix)

            # Prepare details for display
            anonymization_details = []
            for i, tags in enumerate(all_anonymized_tags):
                if tags:
                    details = f"File {i+1}: " + ", ".join([f"{k}: {v}" for k, v in tags.items()])
                    anonymization_details.append(details)

                    # Update progress
                    progress.setValue(i + 1)

                    # Check if user cancelled
                    if progress.wasCanceled():
                        break

            # Close progress dialog
            progress.close()

            # Show summary
            if anonymization_details:
                summary = "Anonymized tags:\n" + "\n".join(anonymization_details)
                QMessageBox.information(
                    self, 
                    'Folder Anonymization', 
                    f'Successfully anonymized {len(anonymization_details)} files with prefix: {prefix}\n\n{summary}'
                )
            else:
                QMessageBox.warning(self, 'Anonymization', 'No files were anonymized.')

        except Exception as e:
            QMessageBox.critical(self, 'Anonymization Error', f'An error occurred: {e}')

        # Refresh the current image display and tags
        self.update_image()
        self.display_tags()


    def open_dicom_folder(self):
        """
        Open a folder containing DICOM files and load them.
        """
        folder_path = QFileDialog.getExistingDirectory(self, 'Select DICOM Folder')
        if folder_path:
            dicom_files = self.dicom_handler.load_dicom_folder(folder_path)
            if not dicom_files:
                QMessageBox.warning(self, 'No DICOM Files', 'No DICOM files found in the selected folder.')
                return

            # Setup slider
            self.image_slider.setMinimum(0)
            self.image_slider.setMaximum(len(dicom_files) - 1)
            self.image_slider.setValue(0)
            self.current_index = 0

            # Update slider label
            self.slider_label.setText(f'Image: 1/{len(dicom_files)}')

            # Display the first image
            self.update_image()
            self.display_tags()

    def update_image(self):
        # Get current slider value
        self.current_index = self.image_slider.value()

        # Check if multi-frame dataset is loaded
        if self.multi_frame_dataset and 'NumberOfFrames' in self.multi_frame_dataset:
            num_frames = int(self.multi_frame_dataset.NumberOfFrames)
            self.slider_label.setText(f'Frame: {self.current_index + 1}/{num_frames}')
            
            # Extract specific frame
            pixel_array = self.multi_frame_dataset.pixel_array[self.current_index]
            
            # Clear previous plot
            self.figure.clear()
            
            # Create new axes
            ax = self.figure.add_subplot(111)
            
            # Display the frame
            img = ax.imshow(pixel_array, cmap='gray')
            ax.set_title(f'Frame {self.current_index + 1}')
            ax.axis('off')
            
            # Tight layout to remove extra white space
            self.figure.tight_layout()
            
            # Redraw the canvas
            self.image_canvas.draw()
            
            # Update tags
            self.display_tags()
        
        # Handle single-frame or folder DICOM files
        else:
            # Get pixel array
            pixel_array = self.dicom_handler.get_image_at_index(self.current_index)

            if pixel_array is not None:
                # Clear previous plot
                self.figure.clear()

                # Create new axes
                ax = self.figure.add_subplot(111)

                # Display the image
                img = ax.imshow(pixel_array, cmap='gray')
                ax.set_title(f'Image {self.current_index + 1}')
                ax.axis('off')

                # Update slider label
                total_images = len(self.dicom_handler.dicom_files)
                self.slider_label.setText(f'Image: {self.current_index + 1}/{total_images}')

                # Tight layout to remove extra white space
                self.figure.tight_layout()

                # Redraw the canvas
                self.image_canvas.draw()

                # Update tags
                self.display_tags()
    def display_tags(self):
        # Get tags for current image
        tags = self.dicom_handler.get_dicom_tags(self.current_index)
        
        # Clear previous tags
        self.tags_table.setRowCount(0)
        self.tags_table.setRowCount(len(tags))
        
        # Populate tags table
        for row, (tag, value) in enumerate(tags.items()):
            self.tags_table.setItem(row, 0, QTableWidgetItem(str(tag)))
            self.tags_table.setItem(row, 1, QTableWidgetItem(str(value)))
        
        self.tags_table.resizeColumnsToContents()

    def search_dicom_tag(self):
        tag = self.tag_search_input.text()
        tags = self.dicom_handler.get_dicom_tags(self.current_index)
        
        # Search for tag
        matching_tags = {k: v for k, v in tags.items() if tag.lower() in k.lower()}
        
        if matching_tags:
            # Show matching tags
            result = '\n'.join([f"{k}: {v}" for k, v in matching_tags.items()])
            QMessageBox.information(self, 'Tag Search Results', result)
        else:
            QMessageBox.warning(self, 'Not Found', f'No tags matching "{tag}" found')

    def anonymize_current_dicom(self):
        prefix = self.anon_prefix_input.text()
        if prefix:
            # Anonymize current file
            anonymized_tags = self.dicom_handler.anonymize_file(self.current_index, prefix)
            
            if anonymized_tags:
                details = '\n'.join([f"{k}: {v}" for k, v in anonymized_tags.items()])
                QMessageBox.information(self, 'Anonymization', 
                                        f'Successfully anonymized current file with prefix: {prefix}\n\n{details}')
            else:
                QMessageBox.warning(self, 'Error', 'Could not anonymize the current file')
        else:
            QMessageBox.warning(self, 'Error', 'Please enter an anonymization prefix')
    
def main():
    app = QApplication(sys.argv)
    viewer = DicomFolderViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()