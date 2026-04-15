import { redirect } from 'next/navigation'

// Legacy /training route — consolidated into Knowledge Core
export default function TrainingRedirect() {
  redirect('/knowledge')
}
