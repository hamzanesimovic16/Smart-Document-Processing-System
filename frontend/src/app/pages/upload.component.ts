import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DocumentsService } from '../documents.service';

const ALLOWED_EXTS = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.csv', '.txt'];

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule, MatIconModule, MatProgressSpinnerModule, MatSnackBarModule],
  template: `
    <mat-card class="upload-card">
      <mat-card-header>
        <mat-card-title>Upload a document</mat-card-title>
        <mat-card-subtitle>PDF, PNG, JPG, CSV or TXT — max ~10MB</mat-card-subtitle>
      </mat-card-header>
      <mat-card-content>
        <div
          class="dropzone"
          [class.dragging]="dragging()"
          [class.uploading]="uploading()"
          (dragover)="$event.preventDefault(); dragging.set(true)"
          (dragleave)="dragging.set(false)"
          (drop)="onDrop($event)"
          (click)="fileInput.click()"
        >
          <input #fileInput type="file" hidden [accept]="acceptList" (change)="onPick($event)" />
          @if (uploading()) {
            <mat-spinner diameter="48"></mat-spinner>
            <p>Processing {{ currentFileName() }}…</p>
            <p class="hint">Parsing → extracting with Gemini → validating</p>
          } @else {
            <mat-icon class="big-icon">cloud_upload</mat-icon>
            <p>Drop a file here or click to browse</p>
            <p class="hint">Supported: {{ ALLOWED_EXTS.join(', ') }}</p>
          }
        </div>
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    .upload-card { max-width: 720px; margin: 24px auto; }
    .dropzone {
      border: 2px dashed #ccc;
      border-radius: 12px;
      padding: 64px 16px;
      text-align: center;
      cursor: pointer;
      transition: all .15s ease;
      margin-top: 16px;
    }
    .dropzone:hover { border-color: #1976d2; background: rgba(25,118,210,0.04); }
    .dropzone.dragging { border-color: #1976d2; background: rgba(25,118,210,0.08); }
    .dropzone.uploading { cursor: progress; }
    .big-icon { font-size: 64px; width: 64px; height: 64px; color: #1976d2; }
    .hint { color: #888; font-size: 0.9em; }
  `]
})
export class UploadComponent {
  private docsService = inject(DocumentsService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  readonly ALLOWED_EXTS = ALLOWED_EXTS;
  acceptList = ALLOWED_EXTS.join(',');
  dragging = signal(false);
  uploading = signal(false);
  currentFileName = signal('');

  onPick(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) {
      this.upload(input.files[0]);
    }
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) this.upload(file);
  }

  private upload(file: File) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      this.snack.open(`Unsupported file type: ${ext}`, 'OK', { duration: 4000 });
      return;
    }
    this.uploading.set(true);
    this.currentFileName.set(file.name);
    this.docsService.upload(file).subscribe({
      next: (doc) => {
        this.snack.open('Document processed', 'OK', { duration: 2000 });
        this.router.navigate(['/documents', doc.id]);
      },
      error: (err) => {
        this.uploading.set(false);
        this.snack.open(`Upload failed: ${err.message}`, 'OK', { duration: 6000 });
      }
    });
  }
}
