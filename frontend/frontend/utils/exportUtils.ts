import jsPDF from 'jspdf';
import * as XLSX from 'xlsx';
import { formatPercentage } from './transformers';

interface Clause {
  clause: string;
  category: string;
  importance: string;
}

interface ComparisonMatch {
  expected: Clause;
  actual: Clause;
  similarity: number;
}

interface ComparisonMismatch {
  expected: Clause;
  actual: Clause | null;
  similarity: number;
}

interface Recommendation {
  text: string;
  priority: string;
  category: string;
}

interface ExportData {
  documentName: string;
  matchPercentage: number;
  riskScore: number;
  matches: ComparisonMatch[];
  mismatches: ComparisonMismatch[];
  recommendations: Recommendation[];
}

export const exportToPdf = (data: ExportData) => {
  const doc = new jsPDF();
  let yPos = 20;
  const lineHeight = 10;
  const margin = 20;
  const pageWidth = doc.internal.pageSize.width;

  // Title
  doc.setFontSize(20);
  doc.text('Contract Analysis Report', pageWidth / 2, yPos, { align: 'center' });
  yPos += lineHeight * 2;

  // Document Info
  doc.setFontSize(12);
  doc.text(`Document: ${data.documentName}`, margin, yPos);
  yPos += lineHeight;
  doc.text(`Match Rate: ${formatPercentage(data.matchPercentage)}`, margin, yPos);
  yPos += lineHeight;
  doc.text(`Risk Score: ${formatPercentage(data.riskScore)}`, margin, yPos);
  yPos += lineHeight * 2;

  // Recommendations Section
  doc.setFontSize(16);
  doc.text('Key Recommendations', margin, yPos);
  yPos += lineHeight;
  doc.setFontSize(12);

  data.recommendations.forEach(rec => {
    // Check if we need a new page
    if (yPos > doc.internal.pageSize.height - margin) {
      doc.addPage();
      yPos = margin;
    }

    doc.text(`• ${rec.category} (${rec.priority}):`, margin, yPos);
    yPos += lineHeight;
    
    // Word wrap the recommendation text
    const splitText = doc.splitTextToSize(rec.text, pageWidth - (margin * 2));
    doc.text(splitText, margin + 5, yPos);
    yPos += (splitText.length * lineHeight) + 5;
  });

  // Matches Section
  if (data.matches.length > 0) {
    yPos += lineHeight;
    doc.setFontSize(16);
    doc.text('Matching Clauses', margin, yPos);
    yPos += lineHeight;
    doc.setFontSize(12);

    data.matches.forEach(match => {
      if (yPos > doc.internal.pageSize.height - margin) {
        doc.addPage();
        yPos = margin;
      }

      const [title] = match.expected.clause.split(':');
      doc.text(`${title} (${formatPercentage(match.similarity * 100)} Match)`, margin, yPos);
      yPos += lineHeight;
    });
  }

  // Mismatches Section
  if (data.mismatches.length > 0) {
    yPos += lineHeight;
    doc.setFontSize(16);
    doc.text('Discrepancies Found', margin, yPos);
    yPos += lineHeight;
    doc.setFontSize(12);

    data.mismatches.forEach(mismatch => {
      if (yPos > doc.internal.pageSize.height - margin) {
        doc.addPage();
        yPos = margin;
      }

      const [title] = mismatch.expected.clause.split(':');
      doc.text(`${title} (${mismatch.actual ? 'Mismatch' : 'Missing'})`, margin, yPos);
      yPos += lineHeight;
    });
  }

  // Save the PDF
  doc.save(`${data.documentName}-analysis.pdf`);
};

export const exportToExcel = (data: ExportData) => {
  // Create workbook
  const wb = XLSX.utils.book_new();

  // Overview Sheet
  const overviewData = [
    ['Contract Analysis Report'],
    [],
    ['Document', data.documentName],
    ['Match Rate', formatPercentage(data.matchPercentage)],
    ['Risk Score', formatPercentage(data.riskScore)],
    [],
    ['Summary'],
    ['Total Clauses', data.matches.length + data.mismatches.length],
    ['Matching Clauses', data.matches.length],
    ['Discrepancies', data.mismatches.length],
  ];
  const overviewSheet = XLSX.utils.aoa_to_sheet(overviewData);
  XLSX.utils.book_append_sheet(wb, overviewSheet, 'Overview');

  // Recommendations Sheet
  const recommendationsData = [
    ['Category', 'Priority', 'Recommendation'],
    ...data.recommendations.map(rec => [
      rec.category,
      rec.priority,
      rec.text,
    ]),
  ];
  const recommendationsSheet = XLSX.utils.aoa_to_sheet(recommendationsData);
  XLSX.utils.book_append_sheet(wb, recommendationsSheet, 'Recommendations');

  // Matches Sheet
  const matchesData = [
    ['Clause', 'Category', 'Priority', 'Similarity'],
    ...data.matches.map(match => {
      const [title] = match.expected.clause.split(':');
      return [
        title,
        match.expected.category,
        match.expected.importance,
        formatPercentage(match.similarity * 100),
      ];
    }),
  ];
  const matchesSheet = XLSX.utils.aoa_to_sheet(matchesData);
  XLSX.utils.book_append_sheet(wb, matchesSheet, 'Matching Clauses');

  // Mismatches Sheet
  const mismatchesData = [
    ['Clause', 'Category', 'Priority', 'Status', 'Expected', 'Actual'],
    ...data.mismatches.map(mismatch => {
      const [title] = mismatch.expected.clause.split(':');
      return [
        title,
        mismatch.expected.category,
        mismatch.expected.importance,
        mismatch.actual ? 'Mismatch' : 'Missing',
        mismatch.expected.clause,
        mismatch.actual?.clause || 'N/A',
      ];
    }),
  ];
  const mismatchesSheet = XLSX.utils.aoa_to_sheet(mismatchesData);
  XLSX.utils.book_append_sheet(wb, mismatchesSheet, 'Discrepancies');

  // Save the file
  XLSX.writeFile(wb, `${data.documentName}-analysis.xlsx`);
}; 