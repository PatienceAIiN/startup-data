import { Component, Inject, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  icon?: string;
  variant?: 'danger' | 'primary';
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  encapsulation: ViewEncapsulation.None,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <div class="confirm-dialog">
      <div class="confirm-icon" [class.danger]="data.variant === 'danger'">
        <mat-icon>{{ data.icon || (data.variant === 'danger' ? 'warning' : 'help_outline') }}</mat-icon>
      </div>
      <h2 class="confirm-title">{{ data.title }}</h2>
      <p class="confirm-message">{{ data.message }}</p>
      <div class="confirm-actions">
        <button mat-stroked-button class="btn-cancel" (click)="cancel()" *ngIf="data.cancelText !== ''">
          {{ data.cancelText || 'Cancel' }}
        </button>
        <button
          mat-flat-button
          class="btn-confirm"
          [class.btn-danger]="data.variant === 'danger'"
          (click)="confirm()"
        >
          {{ data.confirmText || 'Confirm' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog {
      padding: 8px 4px;
      text-align: center;
      min-width: 320px;
    }
    .confirm-icon {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: rgba(52, 211, 153, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px;
      color: #34d399;
    }
    .confirm-icon.danger {
      background: rgba(239, 68, 68, 0.15);
      color: #f87171;
    }
    .confirm-icon mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
    }
    .confirm-title {
      font-size: 20px;
      font-weight: 700;
      margin: 0 0 8px;
      color: var(--text-primary);
    }
    .confirm-message {
      font-size: 14px;
      color: var(--text-secondary);
      margin: 0 0 24px;
      line-height: 1.5;
    }
    .confirm-actions {
      display: flex;
      gap: 12px;
      justify-content: center;
    }
    .btn-cancel {
      min-width: 100px;
      border-color: var(--border) !important;
      color: var(--text-secondary) !important;
    }
    .btn-confirm {
      min-width: 100px;
      background: #10b981 !important;
      color: #fff !important;
    }
    .btn-confirm.btn-danger {
      background: #ef4444 !important;
    }
  `],
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData,
  ) {}

  confirm(): void { this.dialogRef.close(true); }
  cancel(): void { this.dialogRef.close(false); }
}
