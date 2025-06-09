import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import json
import os
import shutil
import sys
import platform
from datetime import datetime
import threading
from pathlib import Path

class PathValidator:
    """Validates paths to prevent system damage"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.setup_dangerous_paths()
    
    def setup_dangerous_paths(self):
        """Define dangerous system paths for different operating systems"""
        self.dangerous_paths = {
            'windows': [
                'c:\\windows', 'c:\\program files', 'c:\\program files (x86)',
                'c:\\system32', 'c:\\syswow64', 'c:\\boot', 'c:\\recovery',
                'c:\\$recycle.bin', 'c:\\pagefile.sys', 'c:\\hiberfil.sys',
                'c:\\programdata\\microsoft', 'c:\\users\\all users',
                'c:\\system volume information'
            ],
            'linux': [
                '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/lib', '/lib64',
                '/etc', '/boot', '/sys', '/proc', '/dev', '/run', '/tmp',
                '/var/log', '/var/run', '/var/lib/dpkg', '/var/cache',
                '/usr/lib', '/usr/share', '/root'
            ],
            'darwin': [  
                '/system', '/library', '/applications', '/usr/bin', '/usr/sbin',
                '/bin', '/sbin', '/etc', '/tmp', '/var', '/dev', '/private',
                '/volumes/macintosh hd/system'
            ]
        }
    
    def is_system_path(self, path):
        """Check if path is a dangerous system path"""
        if not path:
            return False
        
        path_lower = Path(path).resolve().as_posix().lower()
        
        dangerous_list = self.dangerous_paths.get(self.system, [])
        
        for dangerous_path in dangerous_list:
            dangerous_path_normalized = dangerous_path.replace('\\', '/').lower()
            if path_lower.startswith(dangerous_path_normalized):
                return True
        
        return False
    
    def is_root_drive(self, path):
        """Check if path is root drive (C:\ on Windows, / on Unix)"""
        try:
            resolved_path = Path(path).resolve()
            
            if self.system == 'windows':
                return len(str(resolved_path)) <= 3 and str(resolved_path).endswith(':\\')
            else:
                return str(resolved_path) == '/'
        except:
            return False
    
    def has_sufficient_depth(self, path, min_depth=2):
        """Ensure path has minimum directory depth for safety"""
        try:
            parts = Path(path).resolve().parts
            return len(parts) >= min_depth
        except:
            return False
    
    def validate_path(self, path, path_type="backup"):
        """Comprehensive path validation"""
        if not path or not path.strip():
            return False, "Pfad darf nicht leer sein."
        
        path = path.strip()
        
        try:
            path_obj = Path(path)
            
            if self.is_system_path(path):
                return False, f"Gefährlicher Systempfad erkannt! {path_type.capitalize()}-Pfad darf nicht in Systemverzeichnissen liegen."
            
            if self.is_root_drive(path):
                return False, f"Root-Laufwerk als {path_type}-Pfad nicht erlaubt! Bitte einen spezifischen Ordner wählen."
            
            if path_type == "backup" and not self.has_sufficient_depth(path, 3):
                return False, f"Backup-Pfad sollte mindestens 3 Verzeichnisebenen tief sein (z.B. C:\\Backups\\CodeKeeper\\ProjectName)."
            
            parent = path_obj.parent
            if not parent.exists():
                try:
                    parent.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    return False, f"Keine Berechtigung für Verzeichnis: {parent}"
                except Exception as e:
                    return False, f"Kann Verzeichnis nicht erstellen: {str(e)}"
            
            if path_obj.exists() and path_obj.is_file():
                return False, f"Pfad zeigt auf eine Datei, nicht auf ein Verzeichnis: {path}"
            
            return True, "Pfad ist gültig."
            
        except Exception as e:
            return False, f"Pfad-Validierung fehlgeschlagen: {str(e)}"
    
    def suggest_safe_path(self, path_type="backup"):
        """Suggest safe default paths"""
        user_home = Path.home()
        
        suggestions = {
            'backup': user_home / 'CodeKeeper' / 'Backups',
            'source': user_home / 'Development',
            'runtime': user_home / 'Runtime'
        }
        
        return str(suggestions.get(path_type, user_home / 'CodeKeeper'))


class ProjectManager:
    def __init__(self, db_path="codekeeper.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for project storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                source_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                runtime_path TEXT,
                exclude_patterns TEXT,
                last_backup TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_project(self, name, source_path, backup_path, runtime_path="", exclude_patterns=""):
        """Add new project to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO projects (name, source_path, backup_path, runtime_path, exclude_patterns)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, source_path, backup_path, runtime_path, exclude_patterns))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_all_projects(self):
        """Get all projects from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM projects ORDER BY name')
        projects = cursor.fetchall()
        conn.close()
        return projects
    
    def update_last_backup(self, project_id):
        """Update last backup timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE projects SET last_backup = CURRENT_TIMESTAMP WHERE id = ?
        ''', (project_id,))
        conn.commit()
        conn.close()
    
    def delete_project(self, project_id):
        """Delete project from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        conn.close()

class BackupEngine:
    def __init__(self):
        self.exclude_defaults = ['.git', '__pycache__', 'node_modules', '.vs', '.vscode', 'bin', 'obj']
    
    def parse_exclude_patterns(self, exclude_string):
        """Parse exclude patterns from string"""
        if not exclude_string:
            return self.exclude_defaults
        patterns = [p.strip() for p in exclude_string.split(',') if p.strip()]
        return list(set(patterns + self.exclude_defaults))
    
    def should_exclude(self, path, exclude_patterns):
        """Check if path should be excluded"""
        path_parts = Path(path).parts
        for pattern in exclude_patterns:
            if pattern in path_parts or Path(path).name == pattern:
                return True
            if pattern.startswith('*') and Path(path).name.endswith(pattern[1:]):
                return True
        return False
    
    def copy_directory(self, source, destination, exclude_patterns, progress_callback=None, operation_type="backup"):
        """Copy directory with exclusions, progress tracking and safety measures"""
        exclude_patterns = self.parse_exclude_patterns(exclude_patterns)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if operation_type == "backup":
            project_name = Path(source).name
            versioned_destination = os.path.join(destination, f"{project_name}_{timestamp}")
            final_destination = versioned_destination
        else:
            final_destination = destination
            
            if os.path.exists(destination) and os.listdir(destination):
                import tkinter.messagebox as mb
                result = mb.askyesno(
                    "Zielverzeichnis überschreiben?",
                    f"Das Runtime-Verzeichnis enthält bereits Dateien:\n{destination}\n\n"
                    f"Soll der Inhalt überschrieben werden?\n\n"
                    f"WARNUNG: Alle existierenden Dateien gehen verloren!",
                    icon='warning'
                )
                if not result:
                    raise Exception("Deployment abgebrochen: Benutzer hat Überschreibung abgelehnt")
                
                shutil.rmtree(destination)
        
        os.makedirs(final_destination, exist_ok=True)
        
        total_files = sum([len(files) for r, d, files in os.walk(source)])
        copied_files = 0
        
        for root, dirs, files in os.walk(source):
            dirs[:] = [d for d in dirs if not self.should_exclude(os.path.join(root, d), exclude_patterns)]
            
            rel_path = os.path.relpath(root, source)
            dest_dir = os.path.join(final_destination, rel_path) if rel_path != '.' else final_destination
            
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            for file in files:
                source_file = os.path.join(root, file)
                if not self.should_exclude(source_file, exclude_patterns):
                    dest_file = os.path.join(dest_dir, file)
                    try:
                        shutil.copy2(source_file, dest_file)
                        copied_files += 1
                        if progress_callback:
                            progress_callback(copied_files, total_files)
                    except Exception as e:
                        print(f"Error copying {source_file}: {e}")
        
        return copied_files, final_destination

class CodeKeeperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeKeeper - Development Backup System")
        self.root.geometry("900x600")
        
        self.project_manager = ProjectManager()
        self.backup_engine = BackupEngine()
        self.path_validator = PathValidator()
        
        self.setup_ui()
        self.refresh_project_list()
    
    def setup_ui(self):
        """Setup the main UI"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        title_label = ttk.Label(main_frame, text="CodeKeeper - Development Backup System", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        list_frame = ttk.LabelFrame(main_frame, text="Projekte", padding="5")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        self.project_tree = ttk.Treeview(list_frame, columns=('source', 'backup', 'last_backup'), show='tree headings')
        self.project_tree.heading('#0', text='Projekt')
        self.project_tree.heading('source', text='Quelle')
        self.project_tree.heading('backup', text='Backup')
        self.project_tree.heading('last_backup', text='Letztes Backup')
        
        self.project_tree.column('#0', width=150)
        self.project_tree.column('source', width=200)
        self.project_tree.column('backup', width=200)
        self.project_tree.column('last_backup', width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.project_tree.yview)
        self.project_tree.configure(yscrollcommand=scrollbar.set)
        
        self.project_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Button(control_frame, text="Neues Projekt", command=self.add_project_dialog).pack(pady=5, fill=tk.X)
        
        action_frame = ttk.LabelFrame(control_frame, text="Aktionen", padding="5")
        action_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(action_frame, text="Backup erstellen", command=self.create_backup).pack(pady=2, fill=tk.X)
        ttk.Button(action_frame, text="In Runtime kopieren", command=self.deploy_to_runtime).pack(pady=2, fill=tk.X)
        ttk.Button(action_frame, text="Projekt löschen", command=self.delete_project).pack(pady=2, fill=tk.X)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=10, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Bereit")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        log_frame = ttk.LabelFrame(control_frame, text="Log", padding="5")
        log_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def refresh_project_list(self):
        """Refresh the project list"""
        for item in self.project_tree.get_children():
            self.project_tree.delete(item)
        
        projects = self.project_manager.get_all_projects()
        for project in projects:
            last_backup = project[6] if project[6] else "Nie"
            if last_backup != "Nie":
                try:
                    dt = datetime.fromisoformat(last_backup.replace('Z', '+00:00'))
                    last_backup = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    pass
            
            self.project_tree.insert('', tk.END, text=project[1], 
                                   values=(project[2][:30] + "..." if len(project[2]) > 30 else project[2],
                                          project[3][:30] + "..." if len(project[3]) > 30 else project[3],
                                          last_backup),
                                   tags=(project[0],))
    
    def add_project_dialog(self):
        """Open dialog to add new project"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Neues Projekt hinzufügen")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Projektname:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=name_var, width=50).grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(main_frame, text="Quellpfad:").grid(row=1, column=0, sticky=tk.W, pady=5)
        source_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=source_var, width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="...", width=3, 
                  command=lambda: self.safe_directory_dialog(source_var, "source")).grid(row=1, column=2, pady=5)
        
        ttk.Label(main_frame, text="Backup-Pfad:").grid(row=2, column=0, sticky=tk.W, pady=5)
        backup_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=backup_var, width=40).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="...", width=3,
                  command=lambda: self.safe_directory_dialog(backup_var, "backup")).grid(row=2, column=2, pady=5)
        
        ttk.Label(main_frame, text="Runtime-Pfad (optional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        runtime_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=runtime_var, width=40).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        ttk.Button(main_frame, text="...", width=3,
                  command=lambda: self.safe_directory_dialog(runtime_var, "runtime")).grid(row=3, column=2, pady=5)
        
        ttk.Label(main_frame, text="Ausschluss-Muster\n(kommagetrennt):").grid(row=4, column=0, sticky=(tk.W, tk.N), pady=5)
        exclude_var = tk.StringVar(value=".git, __pycache__, node_modules")
        exclude_text = tk.Text(main_frame, height=4, width=40)
        exclude_text.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        exclude_text.insert('1.0', exclude_var.get())
        
        main_frame.columnconfigure(1, weight=1)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)
        
        def save_project():
            if not all([name_var.get(), source_var.get(), backup_var.get()]):
                messagebox.showerror("Fehler", "Bitte füllen Sie alle Pflichtfelder aus!")
                return
            
            source_valid, source_msg = self.path_validator.validate_path(source_var.get(), "source")
            if not source_valid:
                messagebox.showerror("Ungültiger Quellpfad", source_msg)
                return
            
            backup_valid, backup_msg = self.path_validator.validate_path(backup_var.get(), "backup")
            if not backup_valid:
                messagebox.showerror("Ungültiger Backup-Pfad", backup_msg)
                return
            
            if runtime_var.get().strip():
                runtime_valid, runtime_msg = self.path_validator.validate_path(runtime_var.get(), "runtime")
                if not runtime_valid:
                    messagebox.showerror("Ungültiger Runtime-Pfad", runtime_msg)
                    return
            
            if Path(source_var.get()).resolve() == Path(backup_var.get()).resolve():
                messagebox.showerror("Fehler", "Backup-Pfad darf nicht identisch mit dem Quellpfad sein!")
                return
            
            source_path = Path(source_var.get()).resolve()
            backup_path = Path(backup_var.get()).resolve()
            
            try:
                if source_path in backup_path.parents or backup_path in source_path.parents:
                    messagebox.showerror("Fehler", "Backup-Pfad und Quellpfad dürfen nicht ineinander verschachtelt sein!")
                    return
            except:
                pass  
            
            exclude_patterns = exclude_text.get('1.0', tk.END).strip()
            success = self.project_manager.add_project(
                name_var.get(),
                source_var.get(),
                backup_var.get(),
                runtime_var.get(),
                exclude_patterns
            )
            
            if success:
                self.refresh_project_list()
                self.log_message(f"Projekt '{name_var.get()}' hinzugefügt")
                dialog.destroy()
            else:
                messagebox.showerror("Fehler", "Projekt mit diesem Namen existiert bereits!")
        
        ttk.Button(button_frame, text="Speichern", command=save_project).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def safe_directory_dialog(self, var, path_type):
        """Safe directory dialog with path validation"""
        initial_dir = self.path_validator.suggest_safe_path(path_type)
        
        selected_path = filedialog.askdirectory(
            title=f"{path_type.capitalize()}-Verzeichnis wählen",
            initialdir=initial_dir
        )
        
        if selected_path:
            is_valid, message = self.path_validator.validate_path(selected_path, path_type)
            if is_valid:
                var.set(selected_path)
            else:
                messagebox.showwarning("Unsicherer Pfad", 
                    f"Der gewählte Pfad ist nicht sicher:\n\n{message}\n\n"
                    f"Bitte wählen Sie einen anderen Pfad oder erstellen Sie einen neuen Ordner in einem sicheren Bereich.")
    
    def get_selected_project(self):
        """Get currently selected project"""
        selection = self.project_tree.selection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte wählen Sie ein Projekt aus!")
            return None
        
        item = self.project_tree.item(selection[0])
        project_id = item['tags'][0]
        
        projects = self.project_manager.get_all_projects()
        for project in projects:
            if project[0] == project_id:
                return project
        return None
    
    def progress_callback(self, current, total):
        """Update progress bar"""
        progress = (current / total) * 100 if total > 0 else 0
        self.progress_var.set(progress)
        self.root.update_idletasks()
    
    def create_backup(self):
        """Create backup for selected project"""
        project = self.get_selected_project()
        if not project:
            return
        
        def backup_thread():
            try:
                self.status_var.set("Backup wird erstellt...")
                self.log_message(f"Starte Backup für '{project[1]}'")
                
                copied_files, backup_path = self.backup_engine.copy_directory(
                    project[2], project[3], project[5], self.progress_callback, "backup"
                )
                
                self.project_manager.update_last_backup(project[0])
                self.refresh_project_list()
                
                self.log_message(f"Backup abgeschlossen: {copied_files} Dateien kopiert nach {backup_path}")
                self.status_var.set("Backup abgeschlossen")
                messagebox.showinfo("Erfolg", f"Backup erfolgreich erstellt!\n{copied_files} Dateien kopiert.\n\nGespeichert unter:\n{backup_path}")
                
            except Exception as e:
                self.log_message(f"Backup-Fehler: {str(e)}")
                self.status_var.set("Backup fehlgeschlagen")
                messagebox.showerror("Fehler", f"Backup fehlgeschlagen:\n{str(e)}")
            finally:
                self.progress_var.set(0)
        
        threading.Thread(target=backup_thread, daemon=True).start()
    
    def deploy_to_runtime(self):
        """Deploy project to runtime environment"""
        project = self.get_selected_project()
        if not project:
            return
        
        if not project[4]:  
            messagebox.showwarning("Warnung", "Kein Runtime-Pfad für dieses Projekt konfiguriert!")
            return
        
        def deploy_thread():
            try:
                self.status_var.set("Deployment läuft...")
                self.log_message(f"Starte Deployment für '{project[1]}' nach Runtime")
                
                copied_files, deploy_path = self.backup_engine.copy_directory(
                    project[2], project[4], project[5], self.progress_callback, "runtime"
                )
                
                self.log_message(f"Deployment abgeschlossen: {copied_files} Dateien kopiert nach {deploy_path}")
                self.status_var.set("Deployment abgeschlossen")
                messagebox.showinfo("Erfolg", f"Deployment erfolgreich!\n{copied_files} Dateien kopiert.")
                
            except Exception as e:
                self.log_message(f"Deployment-Fehler: {str(e)}")
                self.status_var.set("Deployment fehlgeschlagen")
                if "abgebrochen" in str(e).lower():
                    messagebox.showinfo("Abgebrochen", "Deployment wurde abgebrochen.")
                else:
                    messagebox.showerror("Fehler", f"Deployment fehlgeschlagen:\n{str(e)}")
            finally:
                self.progress_var.set(0)
        
        threading.Thread(target=deploy_thread, daemon=True).start()
    
    def delete_project(self):
        """Delete selected project"""
        project = self.get_selected_project()
        if not project:
            return
        
        if messagebox.askyesno("Bestätigung", f"Projekt '{project[1]}' wirklich löschen?"):
            self.project_manager.delete_project(project[0])
            self.refresh_project_list()
            self.log_message(f"Projekt '{project[1]}' gelöscht")

def main():
    root = tk.Tk()
    app = CodeKeeperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()