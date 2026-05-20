import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard.component').then(m => m.DashboardComponent)
  },
  {
    path: 'upload',
    loadComponent: () => import('./pages/upload.component').then(m => m.UploadComponent)
  },
  {
    path: 'documents/:id',
    loadComponent: () => import('./pages/review.component').then(m => m.ReviewComponent)
  },
  { path: '**', redirectTo: '/dashboard' }
];
