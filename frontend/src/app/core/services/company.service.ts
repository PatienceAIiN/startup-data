import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Company, CompanyFilter, CompanyPage, CompanyStats } from '../models/company.model';

@Injectable({ providedIn: 'root' })
export class CompanyService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/companies`;

  getCompanies(filter: CompanyFilter): Observable<CompanyPage> {
    let params = new HttpParams()
      .set('page', filter.page ?? 1)
      .set('page_size', filter.pageSize ?? 25);

    if (filter.search) params = params.set('search', filter.search);
    if (filter.dateFrom) params = params.set('date_from', filter.dateFrom);
    if (filter.dateTo) params = params.set('date_to', filter.dateTo);
    if (filter.state) params = params.set('state', filter.state);
    if (filter.status) params = params.set('status', filter.status);
    if (filter.isStartup !== undefined) params = params.set('is_startup', String(filter.isStartup));
    if (filter.minScore !== undefined) params = params.set('min_score', String(filter.minScore));

    return this.http.get<CompanyPage>(this.apiUrl, { params });
  }

  getCompany(id: string): Observable<Company> {
    return this.http.get<Company>(`${this.apiUrl}/${id}`);
  }

  getStats(): Observable<CompanyStats> {
    return this.http.get<CompanyStats>(`${this.apiUrl}/stats`);
  }
}
