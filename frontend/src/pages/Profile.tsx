import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  User,
  Shield,
  Key,
  Smartphone,
  Copy,
  Check,
  Loader2,
  ShieldCheck,
  ShieldOff,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react'
import { authAPI } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface TwoFASetup {
  secret: string
  qr_code: string
  uri: string
}

interface TwoFAStatus {
  enabled: boolean
  backup_codes_remaining: number
}

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState<'info' | 'password' | '2fa'>('info')

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

  // 2FA state
  const [setupData, setSetupData] = useState<TwoFASetup | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [disablePassword, setDisablePassword] = useState('')
  const [regeneratePassword, setRegeneratePassword] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [showBackupCodes, setShowBackupCodes] = useState(false)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  // 2FA Status Query
  const { data: twoFAStatus, refetch: refetchStatus } = useQuery<TwoFAStatus>({
    queryKey: ['2fa-status'],
    queryFn: async () => {
      const res = await authAPI.get2FAStatus()
      return res.data
    },
  })

  // Password Change Mutation
  const changePasswordMutation = useMutation({
    mutationFn: () => authAPI.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setPasswordSuccess('Password changed successfully!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => setPasswordSuccess(''), 3000)
    },
    onError: (err: any) => {
      setPasswordError(err.response?.data?.error || 'Error changing password')
    },
  })

  // 2FA Setup Mutation
  const setup2FAMutation = useMutation({
    mutationFn: () => authAPI.setup2FA(),
    onSuccess: (res) => {
      setSetupData(res.data)
    },
  })

  // 2FA Verify Mutation
  const verify2FAMutation = useMutation({
    mutationFn: (code: string) => authAPI.verify2FA(code),
    onSuccess: (res) => {
      setBackupCodes(res.data.backup_codes)
      setShowBackupCodes(true)
      setSetupData(null)
      setTotpCode('')
      refetchStatus()
      refreshUser()
    },
  })

  // 2FA Disable Mutation
  const disable2FAMutation = useMutation({
    mutationFn: (password: string) => authAPI.disable2FA(password),
    onSuccess: () => {
      setDisablePassword('')
      refetchStatus()
      refreshUser()
    },
  })

  // Regenerate Backup Codes Mutation
  const regenerateCodesMutation = useMutation({
    mutationFn: (password: string) => authAPI.regenerateBackupCodes(password),
    onSuccess: (res) => {
      setBackupCodes(res.data.backup_codes)
      setShowBackupCodes(true)
      setRegeneratePassword('')
      refetchStatus()
    },
  })

  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError('')

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }

    if (newPassword.length < 6) {
      setPasswordError('New password must be at least 6 characters')
      return
    }

    changePasswordMutation.mutate()
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(text)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const copyAllBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'))
    setCopiedCode('all')
    setTimeout(() => setCopiedCode(null), 2000)
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">My Profile</h1>
        <p className="text-muted-foreground">
          Manage your information and security
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2">
        <button
          onClick={() => setActiveTab('info')}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
            activeTab === 'info'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-secondary'
          }`}
        >
          <User className="w-4 h-4" />
          Information
        </button>
        <button
          onClick={() => setActiveTab('password')}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
            activeTab === 'password'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-secondary'
          }`}
        >
          <Key className="w-4 h-4" />
          Password
        </button>
        <button
          onClick={() => setActiveTab('2fa')}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
            activeTab === '2fa'
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-secondary'
          }`}
        >
          <Shield className="w-4 h-4" />
          2FA
          {twoFAStatus?.enabled && (
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
          )}
        </button>
      </div>

      {/* Info Tab */}
      {activeTab === 'info' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Account Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-2xl font-bold text-primary-foreground">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <div>
                <h2 className="text-xl font-semibold">{user?.username}</h2>
                <p className="text-muted-foreground">{user?.email}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-4">
              <div className="p-4 rounded-lg bg-secondary/30">
                <p className="text-sm text-muted-foreground">Role</p>
                <p className="font-medium capitalize">{user?.role}</p>
              </div>
              <div className="p-4 rounded-lg bg-secondary/30">
                <p className="text-sm text-muted-foreground">Status</p>
                <p className="font-medium">
                  {user?.active ? (
                    <span className="text-green-500">Active</span>
                  ) : (
                    <span className="text-red-500">Inactive</span>
                  )}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-secondary/30">
                <p className="text-sm text-muted-foreground">2FA</p>
                <p className="font-medium">
                  {user?.totp_enabled ? (
                    <span className="text-green-500 flex items-center gap-1">
                      <ShieldCheck className="w-4 h-4" />
                      Enabled
                    </span>
                  ) : (
                    <span className="text-yellow-500 flex items-center gap-1">
                      <ShieldOff className="w-4 h-4" />
                      Disabled
                    </span>
                  )}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-secondary/30">
                <p className="text-sm text-muted-foreground">Last Login</p>
                <p className="font-medium text-sm">
                  {user?.last_login
                    ? new Date(user.last_login).toLocaleString('en-US')
                    : 'N/A'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Password Tab */}
      {activeTab === 'password' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Change Password</CardTitle>
            <CardDescription>
              Choose a strong password with at least 6 characters
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
              {passwordError && (
                <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="p-3 rounded-lg bg-green-500/10 text-green-500 text-sm flex items-center gap-2">
                  <Check className="w-4 h-4" />
                  {passwordSuccess}
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">Current Password</label>
                <div className="relative">
                  <Input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showCurrentPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">New Password</label>
                <div className="relative">
                  <Input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showNewPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Confirm New Password</label>
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={changePasswordMutation.isPending}
              >
                {changePasswordMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Change Password'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* 2FA Tab */}
      {activeTab === '2fa' && (
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Two-Factor Authentication (2FA)
              </CardTitle>
              <CardDescription>
                Add an extra layer of security to your account
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30">
                <div className="flex items-center gap-3">
                  <Smartphone className="w-8 h-8 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Authenticator App</p>
                    <p className="text-sm text-muted-foreground">
                      Google Authenticator, Authy, etc.
                    </p>
                  </div>
                </div>
                {twoFAStatus?.enabled ? (
                  <span className="flex items-center gap-2 text-green-500 font-medium">
                    <ShieldCheck className="w-5 h-5" />
                    Enabled
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-yellow-500 font-medium">
                    <ShieldOff className="w-5 h-5" />
                    Disabled
                  </span>
                )}
              </div>

              {twoFAStatus?.enabled && (
                <p className="text-sm text-muted-foreground mt-4">
                  Backup codes remaining: {twoFAStatus.backup_codes_remaining}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Setup 2FA */}
          {!twoFAStatus?.enabled && !setupData && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Enable 2FA</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">
                  Click the button below to start setting up 2FA.
                  You will need an authenticator app like Google
                  Authenticator or Authy.
                </p>
                <Button
                  onClick={() => setup2FAMutation.mutate()}
                  disabled={setup2FAMutation.isPending}
                >
                  {setup2FAMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4 mr-2" />
                      Setup 2FA
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          )}

          {/* QR Code Setup */}
          {setupData && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Setup Your Authenticator</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col items-center gap-4">
                  <p className="text-center text-muted-foreground">
                    Scan the QR code below with your authenticator app:
                  </p>
                  <div className="bg-white p-4 rounded-lg">
                    <img src={setupData.qr_code} alt="QR Code 2FA" className="w-48 h-48" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">
                      Or enter the code manually:
                    </p>
                    <div className="flex items-center gap-2 justify-center">
                      <code className="bg-secondary px-3 py-2 rounded font-mono text-sm">
                        {setupData.secret}
                      </code>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(setupData.secret)}
                      >
                        {copiedCode === setupData.secret ? (
                          <Check className="w-4 h-4 text-green-500" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="border-t border-border pt-4 space-y-4">
                  <p className="text-sm font-medium">
                    Enter the 6-digit code from your authenticator:
                  </p>
                  <div className="flex gap-2 max-w-xs">
                    <Input
                      type="text"
                      placeholder="000000"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      className="text-center text-xl tracking-widest font-mono"
                    />
                    <Button
                      onClick={() => verify2FAMutation.mutate(totpCode)}
                      disabled={totpCode.length !== 6 || verify2FAMutation.isPending}
                    >
                      {verify2FAMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'Verify'
                      )}
                    </Button>
                  </div>
                  {verify2FAMutation.isError && (
                    <p className="text-sm text-destructive">
                      Invalid code. Please try again.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Backup Codes Modal */}
          {showBackupCodes && backupCodes.length > 0 && (
            <Card className="border-yellow-500/50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-yellow-500">
                  <AlertCircle className="w-5 h-5" />
                  Backup Codes
                </CardTitle>
                <CardDescription>
                  Save these codes in a safe place. You can use them to
                  access your account if you lose access to your authenticator.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  {backupCodes.map((code, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-2 bg-secondary/50 rounded font-mono text-sm"
                    >
                      <span>{code}</span>
                      <button
                        onClick={() => copyToClipboard(code)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        {copiedCode === code ? (
                          <Check className="w-4 h-4 text-green-500" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={copyAllBackupCodes}>
                    {copiedCode === 'all' ? (
                      <>
                        <Check className="w-4 h-4 mr-2 text-green-500" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-2" />
                        Copy All
                      </>
                    )}
                  </Button>
                  <Button onClick={() => setShowBackupCodes(false)}>
                    I Understand, I Saved the Codes
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Regenerate Backup Codes */}
          {twoFAStatus?.enabled && !showBackupCodes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Regenerate Backup Codes</CardTitle>
                <CardDescription>
                  Generate new codes if you lost or used the previous ones
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2 max-w-md">
                  <Input
                    type="password"
                    placeholder="Enter your password"
                    value={regeneratePassword}
                    onChange={(e) => setRegeneratePassword(e.target.value)}
                  />
                  <Button
                    variant="outline"
                    onClick={() => regenerateCodesMutation.mutate(regeneratePassword)}
                    disabled={!regeneratePassword || regenerateCodesMutation.isPending}
                  >
                    {regenerateCodesMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      'Regenerate'
                    )}
                  </Button>
                </div>
                {regenerateCodesMutation.isError && (
                  <p className="text-sm text-destructive">
                    Incorrect password. Please try again.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Disable 2FA */}
          {twoFAStatus?.enabled && !showBackupCodes && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-lg text-destructive">Disable 2FA</CardTitle>
                <CardDescription>
                  This will remove extra protection from your account
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2 max-w-md">
                  <Input
                    type="password"
                    placeholder="Enter your password"
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                  />
                  <Button
                    variant="destructive"
                    onClick={() => disable2FAMutation.mutate(disablePassword)}
                    disabled={!disablePassword || disable2FAMutation.isPending}
                  >
                    {disable2FAMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      'Disable'
                    )}
                  </Button>
                </div>
                {disable2FAMutation.isError && (
                  <p className="text-sm text-destructive">
                    Incorrect password. Please try again.
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
