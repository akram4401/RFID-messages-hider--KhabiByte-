import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import re
import math

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VigenereCipher:
    @staticmethod
    def encrypt(text, key):
        """Encrypt text using Vigenère cipher"""
        if not key:
            return text
        
        result = ""
        key = key.upper()
        key_index = 0
        
        for char in text:
            if char.isalpha():
                # Get the shift value from the key
                shift = ord(key[key_index % len(key)]) - ord('A')
                
                if char.isupper():
                    result += chr((ord(char) - ord('A') + shift) % 26 + ord('A'))
                else:
                    result += chr((ord(char) - ord('a') + shift) % 26 + ord('a'))
                
                key_index += 1
            else:
                result += char
        
        return result
    
    @staticmethod
    def decrypt(text, key):
        """Decrypt text using Vigenère cipher"""
        if not key:
            return text
        
        result = ""
        key = key.upper()
        key_index = 0
        
        for char in text:
            if char.isalpha():
                # Get the shift value from the key
                shift = ord(key[key_index % len(key)]) - ord('A')
                
                if char.isupper():
                    result += chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
                else:
                    result += chr((ord(char) - ord('a') - shift) % 26 + ord('a'))
                
                key_index += 1
            else:
                result += char
        
        return result

class RFIDManager:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("KhabiByte")
        self.root.geometry("950x750")
        self.root.resizable(True, True)
        
        # Serial connection
        self.serial_connection = None
        self.is_connected = False
        
        # Variables
        self.encrypt_var = ctk.BooleanVar()
        self.decrypt_var = ctk.BooleanVar()
        self.port_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Disconnected")
        
        # Encryption keys
        self.encryption_key = ""
        self.decryption_key = ""
        
        # RFID Configuration - Using multiple blocks for longer messages
        self.MAX_MESSAGE_LENGTH = 240  # 15 blocks × 16 bytes = 240 characters
        self.BLOCKS_PER_SECTOR = 3  # Using blocks 0, 1, 2 (block 3 is sector trailer)
        self.BYTES_PER_BLOCK = 16
        
        self.setup_ui()
        self.refresh_ports()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main container with proper padding
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame, 
            text="KhabiByte", 
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(15, 20))
        
        # Connection Frame
        conn_frame = ctk.CTkFrame(main_frame)
        conn_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(conn_frame, text="Serial Connection", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 8))
        
        # Port selection
        port_frame = ctk.CTkFrame(conn_frame)
        port_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(port_frame, text="Port:").pack(side="left", padx=(10, 5))
        self.port_combo = ctk.CTkComboBox(port_frame, variable=self.port_var, width=150)
        self.port_combo.pack(side="left", padx=5)
        
        refresh_btn = ctk.CTkButton(port_frame, text="Refresh", command=self.refresh_ports, width=80)
        refresh_btn.pack(side="left", padx=5)
        
        self.connect_btn = ctk.CTkButton(port_frame, text="Connect", command=self.toggle_connection, width=100)
        self.connect_btn.pack(side="left", padx=5)
        
        # Status
        self.status_label = ctk.CTkLabel(conn_frame, textvariable=self.status_var, font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 10))
        
        # Main content frame with proper sizing
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(content_frame)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Write tab
        self.write_tab = self.notebook.add("Write Data")
        self.setup_write_tab()
        
        # Read tab
        self.read_tab = self.notebook.add("Read Data")
        self.setup_read_tab()
        
    def setup_write_tab(self):
        """Setup the write data tab with scrolling"""
        # Create scrollable frame for write tab
        self.write_scroll = ctk.CTkScrollableFrame(self.write_tab)
        self.write_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Encryption section
        encrypt_frame = ctk.CTkFrame(self.write_scroll)
        encrypt_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.encrypt_checkbox = ctk.CTkCheckBox(
            encrypt_frame, 
            text="Encrypt Message", 
            variable=self.encrypt_var,
            command=self.on_encrypt_toggle,
            font=ctk.CTkFont(size=14)
        )
        self.encrypt_checkbox.pack(pady=15)
        
        # Key display frame
        self.key_frame = ctk.CTkFrame(encrypt_frame)
        self.key_label = ctk.CTkLabel(self.key_frame, text="", font=ctk.CTkFont(size=12))
        self.key_label.pack(pady=8)
        
        # Message input section
        msg_frame = ctk.CTkFrame(self.write_scroll)
        msg_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            msg_frame, 
            text=f"Message to Write (Max {self.MAX_MESSAGE_LENGTH} characters):", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.message_text = ctk.CTkTextbox(msg_frame, height=200, font=ctk.CTkFont(size=12))
        self.message_text.pack(fill="x", padx=15, pady=(0, 10))
        
        # Character counter
        self.char_count_label = ctk.CTkLabel(
            msg_frame, 
            text=f"Characters: 0/{self.MAX_MESSAGE_LENGTH}", 
            font=ctk.CTkFont(size=11)
        )
        self.char_count_label.pack(anchor="e", padx=15, pady=(0, 10))
        
        # Bind text change event
        self.message_text.bind("<KeyRelease>", self.update_char_count)
        
        # Upload button
        self.upload_btn = ctk.CTkButton(
            self.write_scroll, 
            text="Upload to RFID Card", 
            command=self.write_data,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.upload_btn.pack(pady=15)
        
        # Status section
        status_frame = ctk.CTkFrame(self.write_scroll)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(status_frame, text="Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.write_status = ctk.CTkTextbox(status_frame, height=120, font=ctk.CTkFont(size=11))
        self.write_status.pack(fill="x", padx=15, pady=(0, 15))
        
    def setup_read_tab(self):
        """Setup the read data tab with scrolling"""
        # Create scrollable frame for read tab
        self.read_scroll = ctk.CTkScrollableFrame(self.read_tab)
        self.read_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Decryption section
        decrypt_frame = ctk.CTkFrame(self.read_scroll)
        decrypt_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        self.decrypt_checkbox = ctk.CTkCheckBox(
            decrypt_frame, 
            text="Message is Encrypted (Vigenère Cipher)", 
            variable=self.decrypt_var,
            command=self.on_decrypt_toggle,
            font=ctk.CTkFont(size=14)
        )
        self.decrypt_checkbox.pack(pady=15)
        
        # Decryption key display frame
        self.decrypt_key_frame = ctk.CTkFrame(decrypt_frame)
        self.decrypt_key_label = ctk.CTkLabel(self.decrypt_key_frame, text="", font=ctk.CTkFont(size=12))
        self.decrypt_key_label.pack(pady=8)
        
        # Read button
        self.read_btn = ctk.CTkButton(
            self.read_scroll, 
            text="Read from RFID Card", 
            command=self.read_data,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled"
        )
        self.read_btn.pack(pady=15)
        
        # Data display section
        data_frame = ctk.CTkFrame(self.read_scroll)
        data_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(data_frame, text="Read Data:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.read_data_text = ctk.CTkTextbox(data_frame, height=200, font=ctk.CTkFont(size=12))
        self.read_data_text.pack(fill="x", padx=15, pady=(0, 10))
        
        # Character count for read data
        self.read_char_count_label = ctk.CTkLabel(data_frame, text="Characters: 0", font=ctk.CTkFont(size=11))
        self.read_char_count_label.pack(anchor="e", padx=15, pady=(0, 10))
        
        # Status section
        status_frame = ctk.CTkFrame(self.read_scroll)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(status_frame, text="Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.read_status = ctk.CTkTextbox(status_frame, height=120, font=ctk.CTkFont(size=11))
        self.read_status.pack(fill="x", padx=15, pady=(0, 15))
        
    def on_encrypt_toggle(self):
        """Handle encryption checkbox toggle"""
        if self.encrypt_var.get():
            # Ask for encryption key immediately
            key = simpledialog.askstring("Encryption Key", "Enter encryption key:", show='*')
            if key:
                self.encryption_key = key
                self.key_frame.pack(fill="x", padx=15, pady=(0, 10))
                self.key_label.configure(text=f"Encryption Key Set: {'*' * len(key)}")
            else:
                # If no key provided, uncheck the box
                self.encrypt_var.set(False)
        else:
            # Hide key display and clear key
            self.key_frame.pack_forget()
            self.encryption_key = ""
            
    def on_decrypt_toggle(self):
        """Handle decryption checkbox toggle"""
        if self.decrypt_var.get():
            # Ask for decryption key immediately
            key = simpledialog.askstring("Decryption Key", "Enter decryption key:", show='*')
            if key:
                self.decryption_key = key
                self.decrypt_key_frame.pack(fill="x", padx=15, pady=(0, 10))
                self.decrypt_key_label.configure(text=f"Decryption Key Set: {'*' * len(key)}")
            else:
                # If no key provided, uncheck the box
                self.decrypt_var.set(False)
        else:
            # Hide key display and clear key
            self.decrypt_key_frame.pack_forget()
            self.decryption_key = ""
            
    def update_char_count(self, event=None):
        """Update character count display"""
        text = self.message_text.get("1.0", "end-1c")
        char_count = len(text)
        self.char_count_label.configure(text=f"Characters: {char_count}/{self.MAX_MESSAGE_LENGTH}")
        
        # Change color if over limit
        if char_count > self.MAX_MESSAGE_LENGTH:
            self.char_count_label.configure(text_color="red")
        else:
            self.char_count_label.configure(text_color=("gray10", "gray90"))
            
    def calculate_blocks_needed(self, message_length):
        """Calculate how many blocks are needed for the message"""
        return math.ceil(message_length / self.BYTES_PER_BLOCK)
        
    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo.configure(values=ports)
        if ports:
            self.port_combo.set(ports[0])
        
    def toggle_connection(self):
        """Toggle serial connection"""
        if not self.is_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
            
    def connect_serial(self):
        """Connect to serial port"""
        try:
            port = self.port_var.get()
            if not port:
                messagebox.showerror("Error", "Please select a port")
                return
                
            self.serial_connection = serial.Serial(port, 9600, timeout=2)
            time.sleep(2)  # Wait for Arduino to initialize
            
            self.is_connected = True
            self.status_var.set(f"Connected to {port}")
            self.connect_btn.configure(text="Disconnect")
            
            # Enable buttons
            self.upload_btn.configure(state="normal")
            self.read_btn.configure(state="normal")
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
            
    def disconnect_serial(self):
        """Disconnect from serial port"""
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            
        self.is_connected = False
        self.status_var.set("Disconnected")
        self.connect_btn.configure(text="Connect")
        
        # Disable buttons
        self.upload_btn.configure(state="disabled")
        self.read_btn.configure(state="disabled")
        
    def write_data(self):
        """Write data to RFID card"""
        if not self.is_connected:
            messagebox.showerror("Error", "Please connect to Arduino first")
            return
            
        message = self.message_text.get("1.0", "end-1c").strip()
        if not message:
            messagebox.showerror("Error", "Please enter a message")
            return
            
        if len(message) > self.MAX_MESSAGE_LENGTH:
            messagebox.showerror("Error", f"Message too long (max {self.MAX_MESSAGE_LENGTH} characters)")
            return
            
        # Handle encryption
        final_message = message
        if self.encrypt_var.get() and self.encryption_key:
            final_message = VigenereCipher.encrypt(message, self.encryption_key)
            
        # Calculate blocks needed
        blocks_needed = self.calculate_blocks_needed(len(final_message))
        
        # Start write operation in separate thread
        threading.Thread(target=self._write_thread, args=(final_message, message, blocks_needed), daemon=True).start()
        
    def _write_thread(self, encrypted_message, original_message, blocks_needed):
        """Write operation in separate thread"""
        try:
            self.root.after(0, lambda: self.write_status.delete("1.0", "end"))
            self.root.after(0, lambda: self.write_status.insert("1.0", "Sending write command to Arduino...\n"))
            
            # Send write command with block count
            self.serial_connection.write(f"WRITE_MULTI:{blocks_needed}\n".encode())
            time.sleep(0.1)
            
            # Send message
            self.serial_connection.write(f"{encrypted_message}\n".encode())
            
            if self.encrypt_var.get():
                self.root.after(0, lambda: self.write_status.insert("end", f"Original: {original_message}\n"))
                self.root.after(0, lambda: self.write_status.insert("end", f"Encrypted: {encrypted_message}\n"))

            self.root.after(0, lambda: self.write_status.insert("end", "Clearing old data blocks...\n"))
            self.root.after(0, lambda: self.write_status.insert("end", f"Writing to {blocks_needed} blocks...\n"))
            self.root.after(0, lambda: self.write_status.insert("end", "Waiting for RFID card... Please place card near reader.\n"))
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 45:  # 45 second timeout for multi-block
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline().decode().strip()
                    self.root.after(0, lambda r=response: self.write_status.insert("end", f"Arduino: {r}\n"))
                    
                    if "successful" in response.lower():
                        self.root.after(0, lambda: messagebox.showinfo("Success", f"Data written successfully to {blocks_needed} blocks!"))
                        return
                    elif "failed" in response.lower():
                        self.root.after(0, lambda: messagebox.showerror("Error", "Write operation failed"))
                        return
                        
                time.sleep(0.1)
                
            self.root.after(0, lambda: messagebox.showerror("Timeout", "Operation timed out. Please try again."))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Write error: {str(e)}"))
            
    def read_data(self):
        """Read data from RFID card"""
        if not self.is_connected:
            messagebox.showerror("Error", "Please connect to Arduino first")
            return
            
        # Start read operation in separate thread
        threading.Thread(target=self._read_thread, daemon=True).start()
        
    def _read_thread(self):
        """Read operation in separate thread"""
        try:
            self.root.after(0, lambda: self.read_status.delete("1.0", "end"))
            self.root.after(0, lambda: self.read_status.insert("1.0", "Sending read command to Arduino...\n"))
            
            # Send read command for multiple blocks
            self.serial_connection.write(b"READ_MULTI\n")
            
            self.root.after(0, lambda: self.read_status.insert("end", "Waiting for RFID card... Please place card near reader.\n"))
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 45:  # 45 second timeout for multi-block
                if self.serial_connection.in_waiting > 0:
                    response = self.serial_connection.readline().decode().strip()
                    self.root.after(0, lambda r=response: self.read_status.insert("end", f"Arduino: {r}\n"))
                    
                    if response.startswith("DATA:"):
                        data = response[5:]  # Remove "DATA:" prefix
                        
                        # Handle decryption if checkbox is checked
                        final_data = data
                        if self.decrypt_var.get() and self.decryption_key:
                            decrypted_data = VigenereCipher.decrypt(data, self.decryption_key)
                            final_data = decrypted_data
                            self.root.after(0, lambda: self.read_status.insert("end", f"Encrypted data: {data}\n"))
                            self.root.after(0, lambda: self.read_status.insert("end", f"Decrypted data: {decrypted_data}\n"))
                        
                        self.root.after(0, lambda d=final_data: self.read_data_text.delete("1.0", "end"))
                        self.root.after(0, lambda d=final_data: self.read_data_text.insert("1.0", d))
                        
                        # Update character count for read data
                        char_count = len(final_data)
                        self.root.after(0, lambda c=char_count: self.read_char_count_label.configure(text=f"Characters: {c}"))
                        return
                    elif "failed" in response.lower():
                        self.root.after(0, lambda: messagebox.showerror("Error", "Read operation failed"))
                        return
                        
                time.sleep(0.1)
                
            self.root.after(0, lambda: messagebox.showerror("Timeout", "Operation timed out. Please try again."))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Read error: {str(e)}"))
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = RFIDManager()
    app.run()
