export interface UserProfile {
  age: number;
  sex: 'female' | 'male';
  is_pregnant: boolean;
  blood_type?: string;
  phone?: string;
  medical_notes?: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'patient' | 'doctor';
  created_at?: string;
  profile?: UserProfile;
}

export interface QualityAssessment {
  score: number;
  status: string;
  sharpness: number;
  brightness: number;
  contrast: number;
  valid: boolean;
}

export interface AnemiaClassification {
  category: string;
  status_key: 'normal' | 'mild' | 'moderate' | 'severe';
  severity: string;
  is_anemic: boolean;
  normal_minimum: number;
  normal_range_text: string;
  color_code: string;
}

export interface Recommendations {
  prevention: string;
  risks: string;
  advice: string;
}

export interface ScreeningResult {
  id?: number;
  screening_id?: number;
  patient_id?: number;
  patient_name?: string;
  screening_type: 'nail' | 'conjunctiva';
  original_image_url: string;
  processed_image_url: string;
  quality?: QualityAssessment;
  quality_status?: string;
  quality_score?: number;
  estimated_hb: number;
  unit: string;
  confidence: number;
  confidence_percentage?: number;
  classification?: AnemiaClassification;
  category?: string;
  is_anemic?: boolean;
  normal_range_text?: string;
  erythema_index?: number | null;
  nail_count?: number;
  color_stats?: any;
  recommendations: Recommendations;
  model_version: string;
  validation_status: string;
  disclaimer: string;
  created_at: string;
}

export interface ArticleItem {
  id: number;
  title: string;
  category: string;
  summary: string;
  content: string;
  read_time: string;
  image_url?: string;
}
