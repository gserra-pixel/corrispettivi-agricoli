/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import Papa from 'papaparse';
import { jsPDF } from 'jspdf';
import 'jspdf-autotable';
import { format, parse, isValid } from 'date-fns';
import { it } from 'date-fns/locale';
import { 
  Upload, 
  FileText, 
  CreditCard, 
  Receipt, 
  Download, 
  AlertCircle, 
  CheckCircle2,
  ChevronRight,
  TrendingUp,
  Wallet,
  ArrowRightLeft
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// --- Utility ---
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- Types ---
interface NoteEntry {
  date: string;
  method: string;
  amount: number;
}

interface SumUpEntry {
  date: string;
  amount: number;
}

interface BillyEntry {
  date: string;
  total: number;
  pos: number;
  cash: number;
}

interface AggregatedDay {
  date: string;
  noteTotal: number;
  sumUpTotal: number;
  billyTotal: number;
  billyPos: number;
  billyCash: number;
  difference: number;
}

// --- Components ---

const FileUploader = ({ 
  label, 
  icon: Icon, 
  onFileSelect, 
  fileName,
  colorClass 
}: { 
  label: string; 
  icon: any; 
  onFileSelect: (file: File) => void;
  fileName: string | null;
  colorClass: string;
}) => {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 ml-1">
        {label}
      </label>
      <div 
        className={cn(
          "relative group cursor-pointer border-2 border-dashed rounded-2xl p-6 transition-all duration-300 flex flex-col items-center justify-center gap-3 bg-white hover:bg-slate-50",
          fileName ? "border-emerald-200 bg-emerald-50/30" : "border-slate-200 hover:border-slate-300"
        )}
      >
        <input 
          type="file" 
          accept=".csv"
          onChange={(e) => e.target.files?.[0] && onFileSelect(e.target.files[0])}
          className="absolute inset-0 opacity-0 cursor-pointer z-10"
        />
        <div className={cn("p-3 rounded-xl", colorClass)}>
          <Icon className="w-6 h-6" />
        </div>
        <div className="text-center">
          <p className="text-sm font-medium text-slate-700">
            {fileName || "Seleziona file CSV"}
          </p>
          <p className="text-xs text-slate-400 mt-1">Trascina o clicca per caricare</p>
        </div>
        {fileName && (
          <div className="absolute top-3 right-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          </div>
        )}
      </div>
    </div>
  );
};

const StatCard = ({ label, value, icon: Icon, colorClass }: { label: string; value: string; icon: any; colorClass: string }) => (
  <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-4">
    <div className={cn("p-3 rounded-xl", colorClass)}>
      <Icon className="w-6 h-6" />
    </div>
    <div>
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
    </div>
  </div>
);

export default function App() {
  const [noteFile, setNoteFile] = useState<File | null>(null);
  const [sumUpFile, setSumUpFile] = useState<File | null>(null);
  const [billyFile, setBillyFile] = useState<File | null>(null);

  const [noteData, setNoteData] = useState<NoteEntry[]>([]);
  const [sumUpData, setSumUpData] = useState<SumUpEntry[]>([]);
  const [billyData, setBillyData] = useState<BillyEntry[]>([]);

  const [isGenerating, setIsGenerating] = useState(false);

  // --- Parsing Logic ---
  const parseCSV = (file: File, type: 'note' | 'sumup' | 'billy') => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const data = results.data as any[];
        
        if (type === 'note') {
          const processed = data.map(row => {
            const dateStr = row['Data'] || row['data'];
            const amount = parseFloat(String(row['Importo'] || row['importo']).replace(',', '.'));
            return {
              date: dateStr,
              method: row['Metodo'] || row['metodo'],
              amount: isNaN(amount) ? 0 : amount
            };
          });
          setNoteData(processed);
        } else if (type === 'sumup') {
          const processed = data.map(row => {
            const dateStr = row['Date'] || row['date'];
            const amount = parseFloat(String(row['Gross amount'] || row['gross amount']).replace(',', '.'));
            return {
              date: dateStr,
              amount: isNaN(amount) ? 0 : amount
            };
          });
          setSumUpData(processed);
        } else if (type === 'billy') {
          const processed = data.map(row => {
            const dateStr = row['Data'] || row['data'];
            const total = parseFloat(String(row['Totale'] || row['totale']).replace(',', '.'));
            const pos = parseFloat(String(row['POS'] || row['pos']).replace(',', '.'));
            const cash = parseFloat(String(row['Contanti'] || row['contanti']).replace(',', '.'));
            return {
              date: dateStr,
              total: isNaN(total) ? 0 : total,
              pos: isNaN(pos) ? 0 : pos,
              cash: isNaN(cash) ? 0 : cash
            };
          });
          setBillyData(processed);
        }
      }
    });
  };

  const handleNoteSelect = (file: File) => {
    setNoteFile(file);
    parseCSV(file, 'note');
  };

  const handleSumUpSelect = (file: File) => {
    setSumUpFile(file);
    parseCSV(file, 'sumup');
  };

  const handleBillySelect = (file: File) => {
    setBillyFile(file);
    parseCSV(file, 'billy');
  };

  // --- Aggregation Logic ---
  const aggregatedData = useMemo(() => {
    const days: Record<string, AggregatedDay> = {};

    // Helper to normalize date strings to YYYY-MM-DD
    const normalizeDate = (d: string) => {
      if (!d) return null;
      // Try common formats: DD/MM/YYYY or YYYY-MM-DD
      let parsed = parse(d, 'dd/MM/yyyy', new Date());
      if (!isValid(parsed)) {
        parsed = parse(d, 'yyyy-MM-dd', new Date());
      }
      return isValid(parsed) ? format(parsed, 'yyyy-MM-dd') : null;
    };

    // Process Note
    noteData.forEach(entry => {
      const d = normalizeDate(entry.date);
      if (!d) return;
      if (!days[d]) days[d] = { date: d, noteTotal: 0, sumUpTotal: 0, billyTotal: 0, billyPos: 0, billyCash: 0, difference: 0 };
      days[d].noteTotal += entry.amount;
    });

    // Process SumUp
    sumUpData.forEach(entry => {
      const d = normalizeDate(entry.date);
      if (!d) return;
      if (!days[d]) days[d] = { date: d, noteTotal: 0, sumUpTotal: 0, billyTotal: 0, billyPos: 0, billyCash: 0, difference: 0 };
      days[d].sumUpTotal += entry.amount;
    });

    // Process Billy
    billyData.forEach(entry => {
      const d = normalizeDate(entry.date);
      if (!d) return;
      if (!days[d]) days[d] = { date: d, noteTotal: 0, sumUpTotal: 0, billyTotal: 0, billyPos: 0, billyCash: 0, difference: 0 };
      days[d].billyTotal += entry.total;
      days[d].billyPos += entry.pos;
      days[d].billyCash += entry.cash;
    });

    // Calculate differences
    return Object.values(days)
      .map(day => ({
        ...day,
        difference: day.noteTotal - day.billyTotal
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [noteData, sumUpData, billyData]);

  const totals = useMemo(() => {
    return aggregatedData.reduce((acc, curr) => ({
      note: acc.note + curr.noteTotal,
      billy: acc.billy + curr.billyTotal,
      pos: acc.pos + curr.sumUpTotal,
      diff: acc.diff + curr.difference
    }), { note: 0, billy: 0, pos: 0, diff: 0 });
  }, [aggregatedData]);

  // --- PDF Generation ---
  const generatePDF = () => {
    if (aggregatedData.length === 0) return;
    setIsGenerating(true);

    try {
      const doc = new jsPDF();
      const firstDate = new Date(aggregatedData[0].date);
      const monthYear = format(firstDate, 'MMMM_yyyy', { locale: it });

      // Header
      doc.setFontSize(18);
      doc.setTextColor(20, 20, 20);
      doc.text('AZIENDA AGRICOLA PEDRA E LUNA', 105, 20, { align: 'center' });
      
      doc.setFontSize(12);
      doc.setTextColor(100, 100, 100);
      doc.text('Regime Speciale IVA art.34 DPR 633/72', 105, 28, { align: 'center' });
      
      doc.setFontSize(14);
      doc.setTextColor(40, 40, 40);
      doc.text(`Report Corrispettivi - ${format(firstDate, 'MMMM yyyy', { locale: it })}`, 105, 40, { align: 'center' });

      // Table
      const tableData = aggregatedData.map(day => [
        format(new Date(day.date), 'dd/MM/yyyy'),
        `€ ${day.billyTotal.toFixed(2)}`,
        `€ ${day.billyPos.toFixed(2)}`,
        `€ ${day.billyCash.toFixed(2)}`,
        `€ ${day.difference.toFixed(2)}`
      ]);

      (doc as any).autoTable({
        startY: 50,
        head: [['Data', 'Totale Corrispettivi', 'Di cui POS', 'Di cui Contanti', 'Differenza']],
        body: tableData,
        theme: 'striped',
        headStyles: { fillColor: [51, 65, 85], textColor: 255 },
        columnStyles: {
          0: { cellWidth: 30 },
          1: { halign: 'right' },
          2: { halign: 'right' },
          3: { halign: 'right' },
          4: { halign: 'right' }
        },
        foot: [[
          'TOTALE', 
          `€ ${totals.billy.toFixed(2)}`, 
          `€ ${aggregatedData.reduce((s, c) => s + c.billyPos, 0).toFixed(2)}`, 
          `€ ${aggregatedData.reduce((s, c) => s + c.billyCash, 0).toFixed(2)}`, 
          `€ ${totals.diff.toFixed(2)}`
        ]],
        footStyles: { fillColor: [241, 245, 249], textColor: 0, fontStyle: 'bold' }
      });

      doc.save(`corrispettivi_${monthYear}.pdf`);
    } catch (error) {
      console.error("PDF Generation Error:", error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-emerald-200">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Pedra e Luna</h1>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Gestione Corrispettivi</p>
            </div>
          </div>
          
          <button
            onClick={generatePDF}
            disabled={aggregatedData.length === 0 || isGenerating}
            className={cn(
              "flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all shadow-sm",
              aggregatedData.length > 0 
                ? "bg-slate-900 text-white hover:bg-slate-800 active:scale-95" 
                : "bg-slate-100 text-slate-400 cursor-not-allowed"
            )}
          >
            {isGenerating ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Download className="w-5 h-5" />
            )}
            Genera Report PDF
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Upload Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FileUploader 
            label="1. Note (Incassi Manuali)" 
            icon={FileText} 
            onFileSelect={handleNoteSelect}
            fileName={noteFile?.name || null}
            colorClass="bg-blue-100 text-blue-600"
          />
          <FileUploader 
            label="2. SumUp (Transazioni POS)" 
            icon={CreditCard} 
            onFileSelect={handleSumUpSelect}
            fileName={sumUpFile?.name || null}
            colorClass="bg-indigo-100 text-indigo-600"
          />
          <FileUploader 
            label="3. Billy (Report Fiscale)" 
            icon={Receipt} 
            onFileSelect={handleBillySelect}
            fileName={billyFile?.name || null}
            colorClass="bg-amber-100 text-amber-600"
          />
        </section>

        {/* Stats Overview */}
        <AnimatePresence>
          {aggregatedData.length > 0 && (
            <motion.section 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
            >
              <StatCard 
                label="Totale Note" 
                value={`€ ${totals.note.toFixed(2)}`} 
                icon={FileText} 
                colorClass="bg-blue-50 text-blue-600"
              />
              <StatCard 
                label="Totale POS (SumUp)" 
                value={`€ ${totals.pos.toFixed(2)}`} 
                icon={CreditCard} 
                colorClass="bg-indigo-50 text-indigo-600"
              />
              <StatCard 
                label="Totale Trasmesso" 
                value={`€ ${totals.billy.toFixed(2)}`} 
                icon={Receipt} 
                colorClass="bg-amber-50 text-amber-600"
              />
              <StatCard 
                label="Differenza Totale" 
                value={`€ ${totals.diff.toFixed(2)}`} 
                icon={ArrowRightLeft} 
                colorClass={totals.diff === 0 ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"}
              />
            </motion.section>
          )}
        </AnimatePresence>

        {/* Data Table */}
        <section className="bg-white rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-6 border-b border-slate-50 flex items-center justify-between">
            <h2 className="text-lg font-bold flex items-center gap-2">
              Dettaglio Giornaliero
              <span className="text-xs font-normal text-slate-400 bg-slate-100 px-2 py-1 rounded-full">
                {aggregatedData.length} giorni elaborati
              </span>
            </h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50">
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Data</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">Note</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">POS (SumUp)</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">Contanti (Billy)</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">Trasmesso (Billy)</th>
                  <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">Differenza</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {aggregatedData.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-20 text-center">
                      <div className="flex flex-col items-center gap-3 text-slate-400">
                        <Upload className="w-12 h-12 opacity-20" />
                        <p className="text-sm">Carica i file CSV per visualizzare i dati</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  aggregatedData.map((day) => (
                    <tr key={day.date} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-6 py-4 font-medium text-slate-900">
                        {format(new Date(day.date), 'dd MMM yyyy', { locale: it })}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-sm">€ {day.noteTotal.toFixed(2)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-indigo-600">€ {day.sumUpTotal.toFixed(2)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-slate-500">€ {day.billyCash.toFixed(2)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm font-bold">€ {day.billyTotal.toFixed(2)}</td>
                      <td className={cn(
                        "px-6 py-4 text-right font-mono text-sm font-bold",
                        day.difference === 0 ? "text-emerald-600" : "text-rose-600"
                      )}>
                        {day.difference > 0 ? '+' : ''}{day.difference.toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Info Section */}
        <section className="bg-blue-50 border border-blue-100 rounded-2xl p-6 flex gap-4">
          <AlertCircle className="w-6 h-6 text-blue-500 shrink-0" />
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-blue-900">Note sulla logica di calcolo</h3>
            <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside opacity-80">
              <li>Il <strong>Totale Trasmesso</strong> è il valore ufficiale preso dal file Billy.</li>
              <li>La <strong>Differenza</strong> viene calcolata come: <code>Note - Billy</code>.</li>
              <li>Eventuali discrepanze sono evidenziate in rosso per facilitare la riconciliazione.</li>
              <li>Assicurarsi che i file CSV utilizzino la virgola o il punto come separatore decimale.</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
