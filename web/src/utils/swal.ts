import Swal from 'sweetalert2';

// Success alert
export const showSuccess = (message: string, title: string = 'Muvaffaqiyat!') => {
  return Swal.fire({
    icon: 'success',
    title: title,
    text: message,
    confirmButtonText: 'OK',
    confirmButtonColor: '#10b981',
  });
};

// Error alert
export const showError = (message: string, title: string = 'Xatolik!') => {
  return Swal.fire({
    icon: 'error',
    title: title,
    text: message,
    confirmButtonText: 'OK',
    confirmButtonColor: '#ef4444',
  });
};

// Warning alert
export const showWarning = (message: string, title: string = 'Ogohlantirish!') => {
  return Swal.fire({
    icon: 'warning',
    title: title,
    text: message,
    confirmButtonText: 'OK',
    confirmButtonColor: '#f59e0b',
  });
};

// Info alert
export const showInfo = (message: string, title: string = 'Ma\'lumot') => {
  return Swal.fire({
    icon: 'info',
    title: title,
    text: message,
    confirmButtonText: 'OK',
    confirmButtonColor: '#3b82f6',
  });
};

// Confirmation dialog
export const showConfirm = (
  message: string,
  title: string = 'Tasdiqlaysizmi?',
  confirmText: string = 'Ha',
  cancelText: string = 'Yo\'q'
) => {
  return Swal.fire({
    icon: 'question',
    title: title,
    text: message,
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: cancelText,
    confirmButtonColor: '#3b82f6',
    cancelButtonColor: '#6b7280',
    reverseButtons: true,
  });
};

// Loading toast
export const showLoading = (message: string = 'Yuklanmoqda...') => {
  Swal.fire({
    title: message,
    allowOutsideClick: false,
    allowEscapeKey: false,
    didOpen: () => {
      Swal.showLoading();
    },
  });
};

// Close any active alert
export const closeAlert = () => {
  Swal.close();
};

// Toast notification (small notification at top-right)
export const showToast = (
  message: string,
  icon: 'success' | 'error' | 'warning' | 'info' = 'success',
  duration: number = 3000
) => {
  const Toast = Swal.mixin({
    toast: true,
    position: 'top-end',
    showConfirmButton: false,
    timer: duration,
    timerProgressBar: true,
    didOpen: (toast) => {
      toast.addEventListener('mouseenter', Swal.stopTimer);
      toast.addEventListener('mouseleave', Swal.resumeTimer);
    },
  });

  return Toast.fire({
    icon: icon,
    title: message,
  });
};
