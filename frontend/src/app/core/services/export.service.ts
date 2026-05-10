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
    dateFrom?: string,
    dateTo?: string,
    state?: string,
    isStartup?: boolean
  ): Observable<ExportResult> {
    let params = new HttpParams();
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);
    if (state) params = params.set('state', state);
    if (isStartup !== undefined) params = params.set('is_startup', String(isStartup));
    return this.http.post<ExportResult>(`${this.apiUrl}/${fileType}`, {}, { params });
  }

  getHistory(): Observable<ExportHistory[]> {
    return this.http.get<ExportHistory[]>(`${this.apiUrl}/history`);
  }
}
