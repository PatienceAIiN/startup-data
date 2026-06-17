import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ExportResult, ExportHistory } from '../models/api-response.model';

@Injectable({ providedIn: 'root' })
export class ExportService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/exports`;

  export(
    fileType: 'csv' | 'xlsx',
    options?: {
      search?: string;
      dateFrom?: string;
      dateTo?: string;
      state?: string;
      city?: string;
      status?: string;
      isStartup?: boolean;
      minScore?: number;
      page?: number;
      pageSize?: number;
    }
  ): Observable<ExportResult> {
    let params = new HttpParams();
    if (options) {
      if (options.search) params = params.set('search', options.search);
      if (options.dateFrom) params = params.set('date_from', options.dateFrom);
      if (options.dateTo) params = params.set('date_to', options.dateTo);
      if (options.state) params = params.set('state', options.state);
      if (options.city) params = params.set('city', options.city);
      if (options.status) params = params.set('status', options.status);
      if (options.isStartup !== undefined) params = params.set('is_startup', String(options.isStartup));
      if (options.minScore !== undefined) params = params.set('min_score', String(options.minScore));
      if (options.page !== undefined) params = params.set('page', String(options.page));
      if (options.pageSize !== undefined) params = params.set('page_size', String(options.pageSize));
    }
    return this.http.post<ExportResult>(`${this.apiUrl}/${fileType}`, {}, { params });
  }

  getHistory(): Observable<ExportHistory[]> {
    return this.http.get<ExportHistory[]>(`${this.apiUrl}/history`);
  }
}
