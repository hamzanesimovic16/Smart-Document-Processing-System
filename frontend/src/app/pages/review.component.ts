import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';

import {
  DocumentDetail,
  DocumentsService,
  DocumentStatus,
  ExtractedData,
  LineItem,
  ValidationIssue
} from '../documents.service';

@Component({
  selector: 'app-review',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatIconModule, MatDividerModule, MatChipsModule,
    MatExpansionModule, MatProgressSpinnerModule, MatSnackBarModule, MatTabsModule,
  ],
  template: `
    @if (loading()) {
      <div class="center"><mat-spinner></mat-spinner></div>
    } @else if (doc()) {
      <div class="header-row">
        <button mat-icon-button (click)="back()"><mat-icon>arrow_back</mat-icon></button>
        <div>
          <h2>{{ doc()!.original_filename }}</h2>
          <mat-chip [class]="'chip-' + statusClass(doc()!.status)">{{ doc()!.status }}</mat-chip>
        </div>
        <span class="spacer"></span>
        <button mat-stroked-button color="primary" (click)="save()" [disabled]="saving()">
          <mat-icon>save</mat-icon> Save corrections
        </button>
        <button mat-flat-button color="primary" (click)="confirm()" [disabled]="saving() || hasErrors()">
          <mat-icon>check</mat-icon> Validate
        </button>
        <button mat-stroked-button color="warn" (click)="reject()" [disabled]="saving()">
          <mat-icon>close</mat-icon> Reject
        </button>
      </div>

      @if (issues().length > 0) {
        <mat-card class="issues-card">
          <mat-card-header><mat-card-title>Validation issues ({{ issues().length }})</mat-card-title></mat-card-header>
          <mat-card-content>
            <ul class="issues-list">
              @for (issue of issues(); track issue.message) {
                <li [class]="'severity-' + issue.severity">
                  <mat-icon>{{ issue.severity === 'error' ? 'error' : 'warning' }}</mat-icon>
                  <strong>{{ issue.field }}:</strong> {{ issue.message }}
                </li>
              }
            </ul>
          </mat-card-content>
        </mat-card>
      } @else {
        <mat-card class="issues-card success">
          <mat-card-content>
            <mat-icon class="ok-icon">check_circle</mat-icon> No validation issues.
          </mat-card-content>
        </mat-card>
      }

      <div class="main-layout">

        <!-- LEFT: preview -->
        <mat-card class="preview-card">
          <mat-card-header><mat-card-title>Document preview</mat-card-title></mat-card-header>
          <mat-card-content class="preview-content">
            @if (isPdf()) {
              <iframe [src]="safeFileUrl()" class="preview-frame" title="Document preview"></iframe>
            } @else if (isImage()) {
              <img [src]="safeFileUrl()" class="preview-img" alt="Document preview" />
            } @else {
              <div class="preview-fallback">
                <mat-icon class="big-icon">insert_drive_file</mat-icon>
                <p>Preview not available for {{ doc()!.file_type }} files.</p>
                <a mat-stroked-button [href]="fileUrl()" target="_blank" download>
                  <mat-icon>download</mat-icon> Download file
                </a>
              </div>
            }
          </mat-card-content>
        </mat-card>

        <!-- RIGHT: fields -->
        <div class="fields-col">
          <mat-card>
            <mat-card-header><mat-card-title>Document fields</mat-card-title></mat-card-header>
            <mat-card-content>
              <mat-form-field>
                <mat-label>Document type</mat-label>
                <mat-select [(ngModel)]="form().document_type">
                  <mat-option value="invoice">Invoice</mat-option>
                  <mat-option value="purchase_order">Purchase Order</mat-option>
                  <mat-option value="unknown">Unknown</mat-option>
                </mat-select>
                @if (issueFor('document_type')) { <mat-hint class="hint-err">⚠ {{ issueFor('document_type') }}</mat-hint> }
              </mat-form-field>

              <mat-form-field>
                <mat-label>Supplier name</mat-label>
                <input matInput [(ngModel)]="form().supplier_name" />
                @if (issueFor('supplier_name')) { <mat-hint class="hint-err">⚠ {{ issueFor('supplier_name') }}</mat-hint> }
              </mat-form-field>

              <mat-form-field>
                <mat-label>Document number</mat-label>
                <input matInput [(ngModel)]="form().document_number" />
                @if (issueFor('document_number')) { <mat-hint class="hint-err">⚠ {{ issueFor('document_number') }}</mat-hint> }
              </mat-form-field>

              <mat-form-field>
                <mat-label>Issue date (YYYY-MM-DD)</mat-label>
                <input matInput [(ngModel)]="form().issue_date" placeholder="2026-01-31" />
                @if (issueFor('issue_date')) { <mat-hint class="hint-err">⚠ {{ issueFor('issue_date') }}</mat-hint> }
              </mat-form-field>

              <mat-form-field>
                <mat-label>Due date (YYYY-MM-DD)</mat-label>
                <input matInput [(ngModel)]="form().due_date" placeholder="2026-02-28" />
                @if (issueFor('due_date')) { <mat-hint class="hint-err">⚠ {{ issueFor('due_date') }}</mat-hint> }
              </mat-form-field>

              <mat-form-field>
                <mat-label>Currency</mat-label>
                <input matInput [(ngModel)]="form().currency" placeholder="EUR" maxlength="3" />
                @if (issueFor('currency')) { <mat-hint class="hint-err">⚠ {{ issueFor('currency') }}</mat-hint> }
              </mat-form-field>
            </mat-card-content>
          </mat-card>

          <mat-card style="margin-top:16px">
            <mat-card-header><mat-card-title>Totals</mat-card-title></mat-card-header>
            <mat-card-content>
              <mat-form-field>
                <mat-label>Subtotal</mat-label>
                <input matInput type="number" [(ngModel)]="form().subtotal" />
                @if (issueFor('subtotal')) { <mat-hint class="hint-err">⚠ {{ issueFor('subtotal') }}</mat-hint> }
              </mat-form-field>
              <mat-form-field>
                <mat-label>Tax</mat-label>
                <input matInput type="number" [(ngModel)]="form().tax" />
              </mat-form-field>
              <mat-form-field>
                <mat-label>Total</mat-label>
                <input matInput type="number" [(ngModel)]="form().total" />
                @if (issueFor('total')) { <mat-hint class="hint-err">⚠ {{ issueFor('total') }}</mat-hint> }
              </mat-form-field>
            </mat-card-content>
          </mat-card>
        </div>
      </div>

      <!-- Line items full width -->
      <mat-card class="line-items-card">
        <mat-card-header>
          <mat-card-title>Line items ({{ form().line_items.length }})</mat-card-title>
          <span class="spacer"></span>
          <button mat-stroked-button (click)="addLine()"><mat-icon>add</mat-icon> Add line</button>
        </mat-card-header>
        <mat-card-content>
          @if (form().line_items.length === 0) {
            <p class="empty">No line items.</p>
          }
          @for (item of form().line_items; track item; let i = $index) {
            <div class="line-row" [class.line-error]="lineHasError(i)">
              <mat-form-field class="desc">
                <mat-label>Description</mat-label>
                <input matInput [(ngModel)]="item.description" />
              </mat-form-field>
              <mat-form-field class="num">
                <mat-label>Qty</mat-label>
                <input matInput type="number" [(ngModel)]="item.quantity" />
              </mat-form-field>
              <mat-form-field class="num">
                <mat-label>Unit price</mat-label>
                <input matInput type="number" [(ngModel)]="item.unit_price" />
              </mat-form-field>
              <mat-form-field class="num">
                <mat-label>Total</mat-label>
                <input matInput type="number" [(ngModel)]="item.total" />
              </mat-form-field>
              <button mat-icon-button color="warn" (click)="removeLine(i)"><mat-icon>delete</mat-icon></button>
            </div>
            @if (lineIssue(i); as msg) {
              <div class="line-issue">⚠ {{ msg }}</div>
            }
          }
        </mat-card-content>
      </mat-card>

      @if (doc()?.raw_text) {
        <mat-expansion-panel class="raw-panel">
          <mat-expansion-panel-header>
            <mat-panel-title>Raw extracted text</mat-panel-title>
            <mat-panel-description>What the parser sent to Gemini</mat-panel-description>
          </mat-expansion-panel-header>
          <pre class="raw-text">{{ doc()!.raw_text }}</pre>
        </mat-expansion-panel>
      }
    } @else {
      <p class="center">Document not found.</p>
    }
  `,
  styles: [`
    .center { display: flex; justify-content: center; padding: 64px; }
    .header-row { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .header-row h2 { margin: 0; }
    .spacer { flex: 1; }
    .issues-card { margin-bottom: 16px; }
    .issues-card.success { background: #f1f8e9; }
    .ok-icon { color: #2e7d32; vertical-align: middle; margin-right: 8px; }
    .issues-list { list-style: none; padding: 0; margin: 0; }
    .issues-list li { padding: 8px 0; display: flex; align-items: center; gap: 8px; }
    .issues-list .severity-error { color: #c62828; }
    .issues-list .severity-warning { color: #ef6c00; }

    /* Two-column layout: preview left, fields right */
    .main-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
    @media (max-width: 1100px) { .main-layout { grid-template-columns: 1fr; } }

    .preview-card mat-card-content { padding: 0; }
    .preview-content { height: 600px; display: flex; align-items: center; justify-content: center; overflow: hidden; }
    .preview-frame { width: 100%; height: 100%; border: none; border-radius: 0 0 4px 4px; }
    .preview-img { max-width: 100%; max-height: 100%; object-fit: contain; padding: 8px; }
    .preview-fallback { text-align: center; color: #888; padding: 32px; }
    .preview-fallback .big-icon { font-size: 64px; width: 64px; height: 64px; color: #ccc; }

    .fields-col { display: flex; flex-direction: column; }
    mat-form-field { width: 100%; margin-bottom: 8px; }
    .hint-err { color: #c62828 !important; }

    .line-items-card { margin-bottom: 16px; }
    .line-items-card mat-card-header { display: flex; align-items: center; }
    .line-row { display: grid; grid-template-columns: 2fr 1fr 1fr 1fr auto; gap: 8px; align-items: center; margin-bottom: 8px; }
    .line-row.line-error { background: #ffebee; padding: 4px; border-radius: 4px; }
    .line-issue { color: #c62828; font-size: 0.85em; margin-bottom: 8px; padding-left: 8px; }
    .empty { text-align: center; color: #888; padding: 16px; }

    .raw-panel { margin-bottom: 32px; }
    .raw-text { white-space: pre-wrap; font-family: ui-monospace, monospace; font-size: 0.85em; background: #f9fafb; padding: 12px; border-radius: 4px; }

    .chip-validated { background: #c8e6c9 !important; color: #1b5e20 !important; }
    .chip-needs-review { background: #ffe0b2 !important; color: #bf360c !important; }
    .chip-rejected { background: #ffcdd2 !important; color: #b71c1c !important; }
    .chip-uploaded { background: #e3f2fd !important; color: #0d47a1 !important; }
  `]
})
export class ReviewComponent {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private docsService = inject(DocumentsService);
  private snack = inject(MatSnackBar);
  private sanitizer = inject(DomSanitizer);

  loading = signal(true);
  saving = signal(false);
  doc = signal<DocumentDetail | null>(null);
  form = signal<ExtractedData>(this.blankForm());
  issues = signal<ValidationIssue[]>([]);

  hasErrors = computed(() => this.issues().some(i => i.severity === 'error'));

  constructor() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (id) this.load(id);
  }

  private blankForm(): ExtractedData {
    return {
      document_type: null, supplier_name: null, document_number: null,
      issue_date: null, due_date: null, currency: null,
      line_items: [], subtotal: null, tax: null, total: null,
    };
  }

  private load(id: number) {
    this.loading.set(true);
    this.docsService.get(id).subscribe({
      next: (d) => {
        this.doc.set(d);
        this.form.set(JSON.parse(JSON.stringify(d.extracted_data)));
        this.issues.set(d.validation_issues);
        this.loading.set(false);
      },
      error: (err) => {
        this.snack.open(`Failed to load: ${err.message}`, 'OK', { duration: 5000 });
        this.loading.set(false);
      }
    });
  }

  fileUrl(): string {
    const id = this.doc()?.id;
    return id ? this.docsService.getFileUrl(id) : '';
  }

  safeFileUrl(): SafeResourceUrl {
    return this.sanitizer.bypassSecurityTrustResourceUrl(this.fileUrl());
  }

  isPdf(): boolean { return this.doc()?.file_type === 'pdf'; }
  isImage(): boolean { return this.doc()?.file_type === 'image'; }

  back() { this.router.navigate(['/dashboard']); }

  save() {
    const id = this.doc()?.id;
    if (!id) return;
    const payload = this.cleanForm(this.form());
    this.saving.set(true);
    this.docsService.update(id, payload).subscribe({
      next: (d) => {
        this.doc.set(d);
        this.form.set(JSON.parse(JSON.stringify(d.extracted_data)));
        this.issues.set(d.validation_issues);
        this.saving.set(false);
        this.snack.open('Saved', 'OK', { duration: 2000 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(`Save failed: ${err.message}`, 'OK', { duration: 5000 });
      }
    });
  }

  confirm() { this.setStatus('Validated'); }
  reject() { this.setStatus('Rejected'); }

  private setStatus(status: DocumentStatus) {
    const id = this.doc()?.id;
    if (!id) return;
    this.saving.set(true);
    this.docsService.setStatus(id, status).subscribe({
      next: (d) => {
        this.doc.set(d);
        this.saving.set(false);
        this.snack.open(`Status: ${status}`, 'OK', { duration: 2000 });
      },
      error: (err) => {
        this.saving.set(false);
        this.snack.open(`Failed: ${err.message}`, 'OK', { duration: 5000 });
      }
    });
  }

  addLine() {
    const f = this.form();
    f.line_items.push({ description: null, quantity: null, unit_price: null, total: null });
    this.form.set({ ...f });
  }

  removeLine(i: number) {
    const f = this.form();
    f.line_items.splice(i, 1);
    this.form.set({ ...f });
  }

  issueFor(field: string): string | null {
    const issue = this.issues().find(i => i.field === field);
    return issue ? issue.message : null;
  }

  lineIssue(i: number): string | null {
    const issue = this.issues().find(iss => iss.field === `line_items[${i}].total`);
    return issue ? issue.message : null;
  }

  lineHasError(i: number): boolean {
    return this.issues().some(iss => iss.field === `line_items[${i}].total` && iss.severity === 'error');
  }

  statusClass(status: string): string {
    return status.toLowerCase().replace(/ /g, '-');
  }

  private cleanForm(data: ExtractedData): ExtractedData {
    const trim = (v: string | null) => (v && v.trim() ? v.trim() : null);
    return {
      ...data,
      supplier_name: trim(data.supplier_name),
      document_number: trim(data.document_number),
      issue_date: trim(data.issue_date),
      due_date: trim(data.due_date),
      currency: trim(data.currency)?.toUpperCase() || null,
      line_items: data.line_items.map(li => ({
        description: trim(li.description),
        quantity: li.quantity,
        unit_price: li.unit_price,
        total: li.total,
      })),
    };
  }
}