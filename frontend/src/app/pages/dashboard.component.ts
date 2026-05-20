import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DocumentsService, DocumentSummary, DocumentStatus, Stats } from '../documents.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatButtonToggleModule,
    MatSnackBarModule,
  ],
  template: `
    @if (loading()) {
      <div class="center"><mat-spinner></mat-spinner></div>
    } @else {
      <div class="stats">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-label">Total</div>
            <div class="stat-value">{{ stats()?.total_documents || 0 }}</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-label">Validated</div>
            <div class="stat-value validated">{{ statusCount('Validated') }}</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-label">Needs Review</div>
            <div class="stat-value warn">{{ statusCount('Needs Review') }}</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-label">Rejected</div>
            <div class="stat-value reject">{{ statusCount('Rejected') }}</div>
          </mat-card-content>
        </mat-card>
      </div>

      @if (currencyTotals().length > 0) {
        <mat-card class="totals-card">
          <mat-card-header><mat-card-title>Validated totals by currency</mat-card-title></mat-card-header>
          <mat-card-content>
            <div class="currency-row">
              @for (entry of currencyTotals(); track entry.currency) {
                <div class="currency-pill">
                  <span class="currency-label">{{ entry.currency }}</span>
                  <span class="currency-amount">{{ entry.total | number:'1.2-2' }}</span>
                </div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      }

      <mat-card class="list-card">
        <mat-card-header>
          <mat-card-title>Documents</mat-card-title>
          <span class="spacer"></span>
          <mat-button-toggle-group [value]="filter()" (change)="setFilter($event.value)">
            <mat-button-toggle value="">All</mat-button-toggle>
            <mat-button-toggle value="Uploaded">Uploaded</mat-button-toggle>
            <mat-button-toggle value="Needs Review">Needs Review</mat-button-toggle>
            <mat-button-toggle value="Validated">Validated</mat-button-toggle>
            <mat-button-toggle value="Rejected">Rejected</mat-button-toggle>
          </mat-button-toggle-group>
        </mat-card-header>
        <mat-card-content>
          @if (filteredDocs().length === 0) {
            <p class="empty">No documents yet. Upload one to get started.</p>
          } @else {
            <table mat-table [dataSource]="filteredDocs()" class="full-width">
              <ng-container matColumnDef="filename">
                <th mat-header-cell *matHeaderCellDef>File</th>
                <td mat-cell *matCellDef="let d">
                  <mat-icon class="file-icon">{{ fileIcon(d.file_type) }}</mat-icon>
                  {{ d.original_filename }}
                </td>
              </ng-container>
              <ng-container matColumnDef="supplier">
                <th mat-header-cell *matHeaderCellDef>Supplier</th>
                <td mat-cell *matCellDef="let d">{{ d.supplier_name || '—' }}</td>
              </ng-container>
              <ng-container matColumnDef="number">
                <th mat-header-cell *matHeaderCellDef>Number</th>
                <td mat-cell *matCellDef="let d">{{ d.document_number || '—' }}</td>
              </ng-container>
              <ng-container matColumnDef="total">
                <th mat-header-cell *matHeaderCellDef>Total</th>
                <td mat-cell *matCellDef="let d">
                  {{ d.total !== null ? (d.total | number:'1.2-2') : '—' }}
                  <span class="muted">{{ d.currency }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let d">
                  <mat-chip [class]="'chip-' + statusClass(d.status)">{{ d.status }}</mat-chip>
                </td>
              </ng-container>
              <ng-container matColumnDef="issues">
                <th mat-header-cell *matHeaderCellDef>Issues</th>
                <td mat-cell *matCellDef="let d">
                  @if (d.issue_count > 0) {
                    <span class="issue-badge">{{ d.issue_count }}</span>
                  } @else {
                    <mat-icon class="ok">check_circle</mat-icon>
                  }
                </td>
              </ng-container>
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let d">
                  <button mat-icon-button (click)="open(d)"><mat-icon>open_in_new</mat-icon></button>
                  <button mat-icon-button color="warn" (click)="del(d, $event)"><mat-icon>delete</mat-icon></button>
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="cols"></tr>
              <tr mat-row *matRowDef="let row; columns: cols;" class="clickable" (click)="open(row)"></tr>
            </table>
          }
        </mat-card-content>
      </mat-card>
    }
  `,
  styles: [`
    .center { display: flex; justify-content: center; padding: 64px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px; }
    .stat-label { font-size: 0.85em; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 2.2em; font-weight: 600; }
    .stat-value.validated { color: #2e7d32; }
    .stat-value.warn { color: #ef6c00; }
    .stat-value.reject { color: #c62828; }
    .totals-card { margin-bottom: 16px; }
    .currency-row { display: flex; gap: 16px; flex-wrap: wrap; }
    .currency-pill { background: #f3f4f6; padding: 12px 20px; border-radius: 8px; }
    .currency-label { font-weight: 600; margin-right: 8px; color: #1976d2; }
    .currency-amount { font-size: 1.2em; }
    .list-card mat-card-header { display: flex; align-items: center; }
    .spacer { flex: 1; }
    .full-width { width: 100%; }
    .file-icon { vertical-align: middle; margin-right: 8px; color: #666; }
    .muted { color: #888; margin-left: 4px; font-size: 0.85em; }
    .clickable { cursor: pointer; }
    .clickable:hover { background: #f9fafb; }
    .empty { text-align: center; color: #888; padding: 32px; }
    .issue-badge { background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 12px; font-weight: 600; }
    .ok { color: #2e7d32; }
    .chip-validated { background: #c8e6c9 !important; color: #1b5e20 !important; }
    .chip-needs-review { background: #ffe0b2 !important; color: #bf360c !important; }
    .chip-rejected { background: #ffcdd2 !important; color: #b71c1c !important; }
    .chip-uploaded { background: #e3f2fd !important; color: #0d47a1 !important; }
  `]
})
export class DashboardComponent {
  private docsService = inject(DocumentsService);
  private router = inject(Router);
  private snack = inject(MatSnackBar);

  loading = signal(true);
  documents = signal<DocumentSummary[]>([]);
  stats = signal<Stats | null>(null);
  filter = signal<string>('');

  cols = ['filename', 'supplier', 'number', 'total', 'status', 'issues', 'actions'];

  filteredDocs = computed(() => {
    const f = this.filter();
    return f ? this.documents().filter(d => d.status === f) : this.documents();
  });

  currencyTotals = computed(() => {
    const s = this.stats();
    if (!s) return [];
    return Object.entries(s.totals_by_currency).map(([currency, total]) => ({ currency, total }));
  });

  constructor() {
    this.refresh();
  }

  refresh() {
    this.loading.set(true);
    forkJoin({ docs: this.docsService.list(), stats: this.docsService.stats() }).subscribe({
      next: ({ docs, stats }) => {
        this.documents.set(docs);
        this.stats.set(stats);
        this.loading.set(false);
      },
      error: (err) => {
        this.snack.open(`Failed to load: ${err.message}`, 'OK', { duration: 6000 });
        this.loading.set(false);
      }
    });
  }

  setFilter(value: string) {
    this.filter.set(value);
  }

  statusCount(s: DocumentStatus): number {
    return this.stats()?.status_counts?.[s] || 0;
  }

  open(d: DocumentSummary) {
    this.router.navigate(['/documents', d.id]);
  }

  del(d: DocumentSummary, event: Event) {
    event.stopPropagation();
    if (!confirm(`Delete ${d.original_filename}?`)) return;
    this.docsService.delete(d.id).subscribe({
      next: () => this.refresh(),
      error: (err) => this.snack.open(`Delete failed: ${err.message}`, 'OK', { duration: 4000 })
    });
  }

  statusClass(status: string): string {
    return status.toLowerCase().replace(/ /g, '-');
  }

  fileIcon(type: string): string {
    switch (type) {
      case 'pdf': return 'picture_as_pdf';
      case 'image': return 'image';
      case 'csv': return 'table_chart';
      case 'txt': return 'description';
      default: return 'insert_drive_file';
    }
  }
}
