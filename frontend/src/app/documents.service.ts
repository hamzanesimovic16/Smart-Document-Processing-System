import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../environments/environment';

export type DocumentStatus = 'Uploaded' | 'Needs Review' | 'Validated' | 'Rejected';
export type DocumentType = 'invoice' | 'purchase_order' | 'unknown';
export type IssueSeverity = 'error' | 'warning';

export interface LineItem {
  description: string | null;
  quantity: number | null;
  unit_price: number | null;
  total: number | null;
}

export interface ExtractedData {
  document_type: DocumentType | null;
  supplier_name: string | null;
  document_number: string | null;
  issue_date: string | null;
  due_date: string | null;
  currency: string | null;
  line_items: LineItem[];
  subtotal: number | null;
  tax: number | null;
  total: number | null;
}

export interface ValidationIssue {
  field: string;
  severity: IssueSeverity;
  message: string;
}

export interface DocumentSummary {
  id: number;
  original_filename: string;
  file_type: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  supplier_name: string | null;
  document_number: string | null;
  total: number | null;
  currency: string | null;
  issue_count: number;
}

export interface DocumentDetail extends DocumentSummary {
  raw_text: string | null;
  extracted_data: ExtractedData;
  validation_issues: ValidationIssue[];
}

export interface Stats {
  total_documents: number;
  status_counts: Record<string, number>;
  totals_by_currency: Record<string, number>;
}

@Injectable({ providedIn: 'root' })
export class DocumentsService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  upload(file: File): Observable<DocumentDetail> {
    const form = new FormData();
    form.append('file', file);
    return this.http.post<DocumentDetail>(`${this.base}/api/documents`, form).pipe(catchError(this.handleError));
  }

  list(statusFilter?: string): Observable<DocumentSummary[]> {
  const params: Record<string, string> = {};
  if (statusFilter) params['status_filter'] = statusFilter;
  return this.http.get<DocumentSummary[]>(`${this.base}/api/documents`, { params }).pipe(catchError(this.handleError));
}

  stats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.base}/api/documents/stats`).pipe(catchError(this.handleError));
  }

  get(id: number): Observable<DocumentDetail> {
    return this.http.get<DocumentDetail>(`${this.base}/api/documents/${id}`).pipe(catchError(this.handleError));
  }

  update(id: number, extracted_data: ExtractedData): Observable<DocumentDetail> {
    return this.http.put<DocumentDetail>(`${this.base}/api/documents/${id}`, { extracted_data }).pipe(catchError(this.handleError));
  }

  setStatus(id: number, status: DocumentStatus): Observable<DocumentDetail> {
    return this.http.put<DocumentDetail>(`${this.base}/api/documents/${id}/status`, { status }).pipe(catchError(this.handleError));
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/api/documents/${id}`).pipe(catchError(this.handleError));
  }

  private handleError(err: HttpErrorResponse) {
    const msg = err.error?.detail || err.message || 'Unknown error';
    return throwError(() => new Error(msg));
  }
}
