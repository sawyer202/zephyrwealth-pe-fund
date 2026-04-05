import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Check, Upload, X, Building2, User, ChevronDown } from 'lucide-react';
import { COUNTRIES } from '../constants/countries';

const API = process.env.REACT_APP_BACKEND_URL;

const INITIAL_FORM = {
  entity_type: 'individual',
  legal_name: '',
  dob: '',
  nationality: '',
  residence_country: '',
  email: '',
  phone: '',
  address: { street: '', city: '', postal_code: '', country: '' },
  net_worth: '',
  annual_income: '',
  source_of_wealth: '',
  investment_experience: '',
  classification: '',
  ubo_declarations: [],
  accredited_declaration: false,
  terms_accepted: false,
};

const INITIAL_FILES = {
  passport: null,
  proof_of_address: null,
  source_of_wealth_doc: null,
  corporate_documents: null,
};

const DOC_LABELS = {
  passport: 'Passport / National ID',
  proof_of_address: 'Proof of Address',
  source_of_wealth_doc: 'Source of Wealth Documentation',
  corporate_documents: 'Corporate Documents',
};

function ProgressBar({ step }) {
  const steps = ['Entity Information', 'Contact Details', 'Investor Profile', 'Documents'];
  return (
    <div className="mb-8">
      <div className="flex items-center gap-0">
        {steps.map((label, i) => {
          const num = i + 1;
          const done = num < step;
          const active = num === step;
          return (
            <React.Fragment key={num}>
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold font-mono border-2 transition-all ${
                  done ? 'bg-[#10B981] border-[#10B981] text-white'
                  : active ? 'bg-[#1B3A6B] border-[#1B3A6B] text-white'
                  : 'bg-white border-[#D1D5DB] text-[#9CA3AF]'
                }`}>
                  {done ? <Check size={14} /> : num}
                </div>
                <span className={`text-xs mt-1.5 font-medium whitespace-nowrap ${active ? 'text-[#1B3A6B]' : done ? 'text-[#10B981]' : 'text-[#9CA3AF]'}`}>
                  {label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <div className={`flex-1 h-0.5 mx-2 mb-5 ${num < step ? 'bg-[#10B981]' : 'bg-[#E5E7EB]'}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="text-xs text-[#EF4444] mt-1">{msg}</p>;
}

function FormInput({ label, required, error, ...props }) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#374151] mb-1.5">
        {label}{required && <span className="text-[#EF4444] ml-0.5">*</span>}
      </label>
      <input
        className={`w-full bg-white border rounded-sm px-3 py-2 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] focus:border-[#1B3A6B] placeholder:text-[#9CA3AF] ${error ? 'border-[#EF4444]' : 'border-[#D1D5DB]'}`}
        {...props}
      />
      <FieldError msg={error} />
    </div>
  );
}

function FormSelect({ label, required, error, children, ...props }) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#374151] mb-1.5">
        {label}{required && <span className="text-[#EF4444] ml-0.5">*</span>}
      </label>
      <select
        className={`w-full bg-white border rounded-sm px-3 py-2 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] focus:border-[#1B3A6B] appearance-none ${error ? 'border-[#EF4444]' : 'border-[#D1D5DB]'}`}
        {...props}
      >
        {children}
      </select>
      <FieldError msg={error} />
    </div>
  );
}

function CountrySelect({ label, required, error, value, onChange, name }) {
  return (
    <FormSelect label={label} required={required} error={error} value={value} onChange={onChange} name={name}>
      <option value="">Select country...</option>
      {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
    </FormSelect>
  );
}

function DropZone({ docType, file, onChange }) {
  const fileRef = useRef();
  const [dragging, setDragging] = useState(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) onChange(docType, f);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div>
      <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
        onChange={(e) => { if (e.target.files[0]) onChange(docType, e.target.files[0]); }} />
      {file ? (
        <div className="flex items-center gap-3 p-3 border border-[#10B981]/30 bg-[#10B981]/5 rounded-sm">
          <div className="w-8 h-8 bg-[#10B981]/10 rounded-sm flex items-center justify-center">
            <Check size={16} className="text-[#10B981]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[#1F2937] truncate">{file.name}</p>
            <p className="text-xs text-[#6B7280] font-mono">{formatSize(file.size)}</p>
          </div>
          <button onClick={() => onChange(docType, null)} className="text-[#6B7280] hover:text-[#EF4444] transition-colors" data-testid={`remove-${docType}`}>
            <X size={16} />
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          data-testid={`dropzone-${docType}`}
          className={`border-2 border-dashed rounded-sm p-5 text-center cursor-pointer transition-all ${dragging ? 'border-[#1B3A6B] bg-[#1B3A6B]/5' : 'border-[#D1D5DB] hover:border-[#1B3A6B] hover:bg-[#F8F9FA]'}`}
        >
          <Upload size={20} className="mx-auto mb-2 text-[#9CA3AF]" />
          <p className="text-sm text-[#6B7280]">Drag & drop or <span className="text-[#1B3A6B] font-medium">browse</span></p>
          <p className="text-xs text-[#9CA3AF] mt-1">PDF, JPG, PNG — max 5MB</p>
        </div>
      )}
    </div>
  );
}

export default function InvestorOnboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(INITIAL_FORM);
  const [files, setFiles] = useState(INITIAL_FILES);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const set = (field, value) => {
    setForm(f => ({ ...f, [field]: value }));
    if (errors[field]) setErrors(e => ({ ...e, [field]: '' }));
  };
  const setAddr = (field, value) => {
    setForm(f => ({ ...f, address: { ...f.address, [field]: value } }));
    if (errors[`address.${field}`]) setErrors(e => ({ ...e, [`address.${field}`]: '' }));
  };

  const setFile = (docType, file) => setFiles(f => ({ ...f, [docType]: file }));

  const addUBO = () => setForm(f => ({ ...f, ubo_declarations: [...f.ubo_declarations, { name: '', nationality: '', ownership_percentage: '' }] }));
  const removeUBO = (i) => setForm(f => ({ ...f, ubo_declarations: f.ubo_declarations.filter((_, idx) => idx !== i) }));
  const updateUBO = (i, field, value) => setForm(f => ({
    ...f,
    ubo_declarations: f.ubo_declarations.map((u, idx) => idx === i ? { ...u, [field]: value } : u),
  }));

  const validateStep = () => {
    const e = {};
    if (step === 1) {
      if (!form.legal_name.trim()) e.legal_name = 'Legal name is required';
      if (!form.dob) e.dob = 'Date is required';
      if (!form.nationality) e.nationality = 'Nationality is required';
      if (!form.residence_country) e.residence_country = 'Residence country is required';
      if (form.entity_type === 'corporate') {
        form.ubo_declarations.forEach((u, i) => {
          if (!u.name.trim()) e[`ubo_${i}_name`] = 'Name required';
          if (!u.nationality) e[`ubo_${i}_nationality`] = 'Nationality required';
          if (!u.ownership_percentage) e[`ubo_${i}_ownership`] = 'Ownership % required';
        });
      }
    }
    if (step === 2) {
      if (!form.email.trim() || !/\S+@\S+\.\S+/.test(form.email)) e.email = 'Valid email required';
      if (!form.phone.trim()) e.phone = 'Phone is required';
      if (!form.address.street.trim()) e['address.street'] = 'Street is required';
      if (!form.address.city.trim()) e['address.city'] = 'City is required';
      if (!form.address.postal_code.trim()) e['address.postal_code'] = 'Postal code is required';
      if (!form.address.country) e['address.country'] = 'Country is required';
    }
    if (step === 3) {
      if (!form.classification) e.classification = 'Classification is required';
      if (!form.net_worth || isNaN(Number(form.net_worth))) e.net_worth = 'Valid net worth required';
      if (!form.annual_income || isNaN(Number(form.annual_income))) e.annual_income = 'Valid annual income required';
      if (!form.source_of_wealth) e.source_of_wealth = 'Source of wealth is required';
      if (!form.investment_experience) e.investment_experience = 'Investment experience is required';
      if (form.classification === 'individual_accredited' && !form.accredited_declaration) {
        e.accredited_declaration = 'You must declare accredited investor status';
      }
    }
    if (step === 4) {
      if (!files.passport) e.passport = 'Passport / National ID is required';
      if (!files.proof_of_address) e.proof_of_address = 'Proof of address is required';
      if (!files.source_of_wealth_doc) e.source_of_wealth_doc = 'Source of wealth documentation is required';
      if (form.entity_type === 'corporate' && !files.corporate_documents) e.corporate_documents = 'Corporate documents are required';
      if (!form.terms_accepted) e.terms_accepted = 'You must accept the Terms & Conditions';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleNext = () => {
    if (validateStep()) setStep(s => s + 1);
  };

  const handleSubmit = async () => {
    if (!validateStep()) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      const payload = {
        ...form,
        net_worth: Number(form.net_worth),
        annual_income: Number(form.annual_income),
        ubo_declarations: form.ubo_declarations.map(u => ({
          ...u, ownership_percentage: Number(u.ownership_percentage),
        })),
      };
      const res = await fetch(`${API}/api/investors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create investor');
      }
      const investor = await res.json();

      for (const [docType, file] of Object.entries(files)) {
        if (!file) continue;
        const fd = new FormData();
        fd.append('file', file);
        fd.append('document_type', docType);
        const docRes = await fetch(`${API}/api/investors/${investor.id}/documents`, {
          method: 'POST',
          credentials: 'include',
          body: fd,
        });
        if (!docRes.ok) console.warn(`Document upload failed for ${docType}`);
      }

      navigate('/investors');
    } catch (err) {
      setSubmitError(err.message || 'Submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      {/* Entity type toggle */}
      <div>
        <label className="block text-sm font-medium text-[#374151] mb-2">Entity Type <span className="text-[#EF4444]">*</span></label>
        <div className="flex gap-2">
          {['individual', 'corporate'].map(t => (
            <button
              key={t}
              type="button"
              onClick={() => set('entity_type', t)}
              data-testid={`entity-type-${t}`}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-sm border text-sm font-medium transition-all ${
                form.entity_type === t
                  ? 'bg-[#1B3A6B] border-[#1B3A6B] text-white'
                  : 'bg-white border-[#D1D5DB] text-[#374151] hover:border-[#1B3A6B]'
              }`}
            >
              {t === 'individual' ? <User size={15} /> : <Building2 size={15} />}
              {t === 'individual' ? 'Individual' : 'Corporate'}
            </button>
          ))}
        </div>
      </div>

      <FormInput
        label="Full Legal Name"
        required
        placeholder={form.entity_type === 'corporate' ? 'e.g. Apex Holdings Ltd' : 'e.g. Victoria Pemberton'}
        value={form.legal_name}
        onChange={e => set('legal_name', e.target.value)}
        error={errors.legal_name}
        data-testid="input-legal-name"
      />

      <FormInput
        label={form.entity_type === 'corporate' ? 'Date of Incorporation' : 'Date of Birth'}
        required
        type="date"
        value={form.dob}
        onChange={e => set('dob', e.target.value)}
        error={errors.dob}
        data-testid="input-dob"
      />

      <div className="grid grid-cols-2 gap-4">
        <CountrySelect
          label="Nationality"
          required
          value={form.nationality}
          onChange={e => set('nationality', e.target.value)}
          error={errors.nationality}
          name="nationality"
        />
        <CountrySelect
          label="Country of Residence"
          required
          value={form.residence_country}
          onChange={e => set('residence_country', e.target.value)}
          error={errors.residence_country}
          name="residence_country"
        />
      </div>

      {/* UBO Section — Corporate only */}
      {form.entity_type === 'corporate' && (
        <div className="border border-[#E5E7EB] rounded-sm p-4 bg-[#F8F9FA]">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-semibold text-[#1F2937]">Beneficial Owners (UBO Declaration)</p>
              <p className="text-xs text-[#6B7280] mt-0.5">Declare all beneficial owners with &gt;10% ownership</p>
            </div>
            <button type="button" onClick={addUBO} data-testid="add-ubo"
              className="text-xs px-3 py-1.5 bg-[#1B3A6B] text-white rounded-sm font-medium hover:bg-[#122A50] transition-colors">
              + Add UBO
            </button>
          </div>
          {form.ubo_declarations.length === 0 && (
            <p className="text-xs text-[#9CA3AF] italic">No UBO declarations added</p>
          )}
          {form.ubo_declarations.map((ubo, i) => (
            <div key={i} className="grid grid-cols-3 gap-3 mb-3 p-3 bg-white border border-[#E5E7EB] rounded-sm">
              <FormInput label="Full Name" required value={ubo.name} onChange={e => updateUBO(i, 'name', e.target.value)} error={errors[`ubo_${i}_name`]} placeholder="Full name" data-testid={`ubo-${i}-name`} />
              <CountrySelect label="Nationality" required value={ubo.nationality} onChange={e => updateUBO(i, 'nationality', e.target.value)} error={errors[`ubo_${i}_nationality`]} name={`ubo_${i}_nationality`} />
              <div className="relative">
                <FormInput label="Ownership %" required type="number" min="0" max="100" value={ubo.ownership_percentage} onChange={e => updateUBO(i, 'ownership_percentage', e.target.value)} error={errors[`ubo_${i}_ownership`]} placeholder="e.g. 55" data-testid={`ubo-${i}-ownership`} />
                <button type="button" onClick={() => removeUBO(i)} className="absolute right-2 top-7 text-[#EF4444] hover:text-red-700" data-testid={`remove-ubo-${i}`}><X size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <FormInput label="Email Address" required type="email" value={form.email} onChange={e => set('email', e.target.value)} error={errors.email} placeholder="investor@example.com" data-testid="input-email" />
        <FormInput label="Phone Number" required value={form.phone} onChange={e => set('phone', e.target.value)} error={errors.phone} placeholder="+1 242-555-0100" data-testid="input-phone" />
      </div>
      <FormInput label="Street Address" required value={form.address.street} onChange={e => setAddr('street', e.target.value)} error={errors['address.street']} placeholder="123 Ocean Drive" data-testid="input-street" />
      <div className="grid grid-cols-3 gap-4">
        <FormInput label="City" required value={form.address.city} onChange={e => setAddr('city', e.target.value)} error={errors['address.city']} placeholder="Nassau" data-testid="input-city" />
        <FormInput label="Postal Code" required value={form.address.postal_code} onChange={e => setAddr('postal_code', e.target.value)} error={errors['address.postal_code']} placeholder="N-1234" data-testid="input-postal" />
        <CountrySelect label="Country" required value={form.address.country} onChange={e => setAddr('country', e.target.value)} error={errors['address.country']} name="addr-country" />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <FormSelect label="Investor Classification" required value={form.classification} onChange={e => set('classification', e.target.value)} error={errors.classification} data-testid="select-classification">
        <option value="">Select classification...</option>
        <option value="individual_accredited">Individual Accredited Investor</option>
        <option value="institutional">Institutional Investor</option>
        <option value="retail">Retail Investor</option>
      </FormSelect>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-[#374151] mb-1.5">Net Worth (USD) <span className="text-[#EF4444]">*</span></label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] text-sm font-mono">$</span>
            <input type="number" value={form.net_worth} onChange={e => set('net_worth', e.target.value)}
              className={`w-full bg-white border rounded-sm pl-6 pr-3 py-2 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] placeholder:text-[#9CA3AF] ${errors.net_worth ? 'border-[#EF4444]' : 'border-[#D1D5DB]'}`}
              placeholder="5000000" data-testid="input-net-worth" />
          </div>
          <FieldError msg={errors.net_worth} />
        </div>
        <div>
          <label className="block text-sm font-medium text-[#374151] mb-1.5">Annual Income (USD) <span className="text-[#EF4444]">*</span></label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] text-sm font-mono">$</span>
            <input type="number" value={form.annual_income} onChange={e => set('annual_income', e.target.value)}
              className={`w-full bg-white border rounded-sm pl-6 pr-3 py-2 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] placeholder:text-[#9CA3AF] ${errors.annual_income ? 'border-[#EF4444]' : 'border-[#D1D5DB]'}`}
              placeholder="500000" data-testid="input-annual-income" />
          </div>
          <FieldError msg={errors.annual_income} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FormSelect label="Source of Wealth" required value={form.source_of_wealth} onChange={e => set('source_of_wealth', e.target.value)} error={errors.source_of_wealth} data-testid="select-source-of-wealth">
          <option value="">Select source...</option>
          <option value="Employment">Employment</option>
          <option value="Business">Business</option>
          <option value="Investment">Investment</option>
          <option value="Inheritance">Inheritance</option>
          <option value="Other">Other</option>
        </FormSelect>
        <FormSelect label="Investment Experience" required value={form.investment_experience} onChange={e => set('investment_experience', e.target.value)} error={errors.investment_experience} data-testid="select-investment-experience">
          <option value="">Select experience...</option>
          <option value="None">None</option>
          <option value="1-3 years">1–3 years</option>
          <option value="3-5 years">3–5 years</option>
          <option value="5+ years">5+ years</option>
        </FormSelect>
      </div>

      {form.classification === 'individual_accredited' && (
        <div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" checked={form.accredited_declaration} onChange={e => set('accredited_declaration', e.target.checked)}
              className="mt-0.5 w-4 h-4 text-[#1B3A6B] border-[#D1D5DB] rounded focus:ring-[#1B3A6B]"
              data-testid="checkbox-accredited" />
            <span className="text-sm text-[#374151]">
              I hereby declare that I qualify as an Accredited Investor in accordance with applicable securities laws, having a net worth exceeding $1,000,000 or annual income exceeding $200,000.
            </span>
          </label>
          <FieldError msg={errors.accredited_declaration} />
        </div>
      )}
    </div>
  );

  const renderStep4 = () => {
    const requiredDocs = ['passport', 'proof_of_address', 'source_of_wealth_doc'];
    if (form.entity_type === 'corporate') requiredDocs.push('corporate_documents');
    return (
      <div className="space-y-5">
        {requiredDocs.map(docType => (
          <div key={docType}>
            <label className="block text-sm font-medium text-[#374151] mb-2">
              {DOC_LABELS[docType]} <span className="text-[#EF4444]">*</span>
            </label>
            <DropZone docType={docType} file={files[docType]} onChange={setFile} />
            <FieldError msg={errors[docType]} />
          </div>
        ))}

        <div className="border-t border-[#E5E7EB] pt-5">
          <label className="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" checked={form.terms_accepted} onChange={e => set('terms_accepted', e.target.checked)}
              className="mt-0.5 w-4 h-4 text-[#1B3A6B] border-[#D1D5DB] rounded focus:ring-[#1B3A6B]"
              data-testid="checkbox-terms" />
            <span className="text-sm text-[#374151]">
              I confirm that all information provided is true, accurate, and complete. I understand that providing false information may result in rejection of this application and may have legal consequences under Bahamian law.
            </span>
          </label>
          <FieldError msg={errors.terms_accepted} />
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="mb-6">
        <button onClick={() => navigate('/investors')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] transition-colors mb-4" data-testid="back-to-investors">
          <ArrowLeft size={15} /> Back to Investors
        </button>
        <p className="text-overline mb-1">Investor Management</p>
        <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">New Investor Onboarding</h1>
        <p className="text-sm text-[#6B7280] mt-1">Step {step} of 4</p>
      </div>

      <div className="max-w-3xl">
        <ProgressBar step={step} />

        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-6">
          <h2 className="text-lg font-semibold text-[#1F2937] mb-6 pb-3 border-b border-[#E5E7EB]">
            {step === 1 && 'Entity Information'}
            {step === 2 && 'Contact Information'}
            {step === 3 && 'Investor Profile'}
            {step === 4 && 'Document Upload'}
          </h2>

          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step === 3 && renderStep3()}
          {step === 4 && renderStep4()}

          {submitError && (
            <div className="mt-4 p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="submit-error">
              {submitError}
            </div>
          )}

          <div className="flex items-center justify-between mt-8 pt-5 border-t border-[#E5E7EB]">
            <button
              onClick={() => step > 1 ? setStep(s => s - 1) : navigate('/investors')}
              className="flex items-center gap-2 px-4 py-2 text-sm text-[#374151] border border-[#D1D5DB] rounded-sm hover:bg-[#F8F9FA] transition-colors"
              data-testid="btn-back"
            >
              <ArrowLeft size={15} /> {step === 1 ? 'Cancel' : 'Back'}
            </button>
            {step < 4 ? (
              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors"
                data-testid="btn-next"
              >
                Next <ArrowRight size={15} />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                data-testid="btn-submit"
                className="flex items-center gap-2 px-6 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {submitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Check size={15} /> Submit for Review
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
