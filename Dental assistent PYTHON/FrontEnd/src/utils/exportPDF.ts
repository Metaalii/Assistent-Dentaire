import type { DentistProfile } from "../hooks/useProfile";

function escapeHtml(text: string): string {
  const htmlEntities: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, (char) => htmlEntities[char] || char);
}

export function exportPDF(
  document: string,
  profile: DentistProfile | null,
  language: string,
  translations: {
    pdfTitle: string;
    pdfDate: string;
    pdfConsultationNotes: string;
    pdfDisclaimer: string;
    pdfConfidential: string;
    professionalTitlePlaceholder: string;
  },
): void {
  const sanitizedContent = escapeHtml(document).replace(/\n/g, '<br>');
  const currentDate = new Date().toLocaleDateString(language === 'fr' ? 'fr-FR' : 'en-GB', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${translations.pdfTitle} - ${currentDate}</title>
      <meta charset="UTF-8">
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          line-height: 1.6;
          color: #1e293b;
          background: #fff;
        }

        .page {
          max-width: 800px;
          margin: 0 auto;
          padding: 40px;
        }

        /* Header */
        .header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding-bottom: 20px;
          border-bottom: 3px solid #2d96c6;
          margin-bottom: 30px;
        }

        .logo-section {
          display: flex;
          align-items: center;
          gap: 15px;
        }

        .logo {
          width: 60px;
          height: 60px;
          background: linear-gradient(135deg, #2d96c6, #28b5ad);
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 28px;
          font-weight: bold;
        }

        .practice-info h1 {
          font-size: 22px;
          font-weight: 700;
          color: #1e293b;
          margin-bottom: 4px;
        }

        .practice-info .title {
          font-size: 14px;
          color: #2d96c6;
          font-weight: 500;
        }

        .contact-info {
          text-align: right;
          font-size: 13px;
          color: #64748b;
        }

        .contact-info p {
          margin-bottom: 3px;
        }

        /* Document Title */
        .document-title {
          background: linear-gradient(135deg, #f0f7fc, #effcfb);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 25px;
          text-align: center;
        }

        .document-title h2 {
          font-size: 20px;
          color: #2d96c6;
          margin-bottom: 8px;
        }

        .document-title .date {
          font-size: 14px;
          color: #64748b;
        }

        /* Content */
        .content-section {
          margin-bottom: 30px;
        }

        .section-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 15px;
          padding-bottom: 10px;
          border-bottom: 2px solid #e2e8f0;
        }

        .section-icon {
          width: 32px;
          height: 32px;
          background: linear-gradient(135deg, #2d96c6, #28b5ad);
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 16px;
        }

        .section-header h3 {
          font-size: 16px;
          font-weight: 600;
          color: #1e293b;
        }

        .content-box {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 10px;
          padding: 20px;
          font-size: 14px;
          line-height: 1.8;
        }

        /* Footer */
        .footer {
          margin-top: 40px;
          padding-top: 20px;
          border-top: 2px solid #e2e8f0;
        }

        .disclaimer {
          background: #fef3c7;
          border: 1px solid #fbbf24;
          border-radius: 8px;
          padding: 12px 16px;
          font-size: 12px;
          color: #92400e;
          margin-bottom: 20px;
        }

        .confidential {
          text-align: center;
          font-size: 11px;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 2px;
        }

        @media print {
          body {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .page {
            padding: 20px;
            max-width: 100%;
          }
          .logo {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
        }
      </style>
    </head>
    <body>
      <div class="page">
        <!-- Header -->
        <div class="header">
          <div class="logo-section">
            <div class="logo">\u{1F9B7}</div>
            <div class="practice-info">
              <h1>${profile?.name || 'Cabinet Dentaire'}</h1>
              <p class="title">${profile?.title || translations.professionalTitlePlaceholder}</p>
            </div>
          </div>
          <div class="contact-info">
            ${profile?.address ? `<p>${escapeHtml(profile.address)}</p>` : ''}
            ${profile?.phone ? `<p>\u{1F4DE} ${escapeHtml(profile.phone)}</p>` : ''}
            ${profile?.email ? `<p>\u{2709}\u{FE0F} ${escapeHtml(profile.email)}</p>` : ''}
          </div>
        </div>

        <!-- Document Title -->
        <div class="document-title">
          <h2>${translations.pdfTitle}</h2>
          <p class="date">${translations.pdfDate}: ${currentDate}</p>
        </div>

        <!-- Content -->
        <div class="content-section">
          <div class="section-header">
            <div class="section-icon">\u{1F4CB}</div>
            <h3>${translations.pdfConsultationNotes}</h3>
          </div>
          <div class="content-box">
            ${sanitizedContent}
          </div>
        </div>

        <!-- Footer -->
        <div class="footer">
          <div class="disclaimer">
            \u{26A0}\u{FE0F} ${translations.pdfDisclaimer}
          </div>
          <p class="confidential">${translations.pdfConfidential}</p>
        </div>
      </div>
    </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
}
