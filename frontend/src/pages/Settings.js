import React from 'react';
import { Settings as SettingsIcon, User, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const roleLabels = {
  compliance: 'Chief Compliance Officer',
  risk: 'Head of Risk',
  manager: 'Fund Manager',
};

export default function Settings() {
  const { user } = useAuth();

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="mb-8">
        <p className="text-overline mb-1">Platform Settings</p>
        <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
          <SettingsIcon size={28} strokeWidth={1.5} color="#1B3A6B" />
          Settings
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="lg:col-span-2 bg-white border border-[#E5E7EB] rounded-sm shadow-sm" data-testid="settings-profile">
          <div className="border-b border-[#E5E7EB] px-5 py-4 flex items-center gap-2">
            <User size={16} strokeWidth={1.5} color="#1B3A6B" />
            <h2 className="text-sm font-semibold text-[#1F2937]">Profile Information</h2>
          </div>
          <div className="px-5 py-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Full Name</label>
              <input
                type="text"
                defaultValue={user?.name || ''}
                readOnly
                className="w-full bg-[#F8F9FA] border border-[#E5E7EB] rounded-sm px-3 py-2 text-sm text-[#1F2937] cursor-not-allowed"
                data-testid="settings-name-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Email Address</label>
              <input
                type="email"
                defaultValue={user?.email || ''}
                readOnly
                className="w-full bg-[#F8F9FA] border border-[#E5E7EB] rounded-sm px-3 py-2 text-sm text-[#1F2937] cursor-not-allowed"
                data-testid="settings-email-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#374151] mb-1.5">Role</label>
              <input
                type="text"
                value={roleLabels[user?.role] || user?.role || ''}
                readOnly
                className="w-full bg-[#F8F9FA] border border-[#E5E7EB] rounded-sm px-3 py-2 text-sm text-[#1F2937] cursor-not-allowed"
                data-testid="settings-role-input"
              />
            </div>
          </div>
        </div>

        {/* Security Card */}
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-5 py-4 flex items-center gap-2">
            <Shield size={16} strokeWidth={1.5} color="#1B3A6B" />
            <h2 className="text-sm font-semibold text-[#1F2937]">Security</h2>
          </div>
          <div className="px-5 py-5 space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-[#F3F4F6]">
              <div>
                <p className="text-sm font-medium text-[#1F2937]">Two-Factor Auth</p>
                <p className="text-xs text-gray-400">Enhance account security</p>
              </div>
              <span className="text-xs font-mono text-gray-400 bg-gray-100 px-2 py-0.5 rounded-sm border border-gray-200">
                Phase 2
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-[#F3F4F6]">
              <div>
                <p className="text-sm font-medium text-[#1F2937]">Session Timeout</p>
                <p className="text-xs text-gray-400">Currently 8 hours</p>
              </div>
              <span className="text-xs font-mono text-[#10B981]">Active</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-[#1F2937]">Audit Logging</p>
                <p className="text-xs text-gray-400">All actions recorded</p>
              </div>
              <span className="text-xs font-mono text-[#10B981]">Enabled</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
