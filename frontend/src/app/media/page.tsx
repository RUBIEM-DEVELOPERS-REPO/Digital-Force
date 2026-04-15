import { redirect } from 'next/navigation'

// Legacy /media route — consolidated into Knowledge Core
export default function MediaRedirect() {
  redirect('/knowledge')
}
