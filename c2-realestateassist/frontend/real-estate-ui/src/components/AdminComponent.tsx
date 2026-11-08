import React from 'react'
import TopBarAdmin from './TopBarAdmin'
import AdminIntro from './AdminIntro'
import PropertyCardsPageAdmin from '../pages/PropertyCardsPageAdmin'

const AdminComponent = () => {
  return (
    <div className='flex flex-col gap-4'>
        <TopBarAdmin/>
        <div className='px-4'>
            <AdminIntro/>
        </div>
        <div className='px-4'>
           <PropertyCardsPageAdmin/>
        </div>

    </div>
  )
}

export default AdminComponent
