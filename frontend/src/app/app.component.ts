import { Component } from '@angular/core';
import { RouterLink, RouterOutlet, RouterLinkActive } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, MatToolbarModule, MatButtonModule, MatIconModule],
  template: `
    <mat-toolbar color="primary">
      <span class="brand">📄 Smart Document Processing</span>
      <span class="spacer"></span>
      <a mat-button routerLink="/dashboard" routerLinkActive="active">
        <mat-icon>dashboard</mat-icon> Dashboard
      </a>
      <a mat-button routerLink="/upload" routerLinkActive="active">
        <mat-icon>upload_file</mat-icon> Upload
      </a>
    </mat-toolbar>
    <main class="container">
      <router-outlet />
    </main>
  `,
  styles: [`
    .spacer { flex: 1; }
    .brand { font-weight: 500; }
    .container { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .active { background: rgba(255,255,255,0.15); }
  `]
})
export class AppComponent {}
