import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ScrapeJob } from '../models/api-response.model';

@Injectable({ providedIn: 'root' })
export class ScraperService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/scraper`;

  trigger(dateFrom?: string, dateTo?: string): Observable<{ job_id: string; status: string; message: string }> {
    let url = `${this.apiUrl}/trigger`;
    const params: string[] = [];
    if (dateFrom) params.push(`date_from=${dateFrom}`);
    if (dateTo) params.push(`date_to=${dateTo}`);
    if (params.length) url += '?' + params.join('&');
    return this.http.post<{ job_id: string; status: string; message: string }>(url, {});
  }

  getStatus(jobId: string): Observable<ScrapeJob> {
    return this.http.get<ScrapeJob>(`${this.apiUrl}/status/${jobId}`);
  }

  listJobs(): Observable<ScrapeJob[]> {
    return this.http.get<ScrapeJob[]>(`${this.apiUrl}/jobs`);
  }
}
